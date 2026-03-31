"""Orchestrator 主循环 — perceive → decide → execute → verify。"""

from __future__ import annotations

import asyncio
import json
import time

from fastmcp import Client
from loguru import logger
from mcp.types import Tool as McpTool

from ahu_paimon_toolkit.capture.window_capture import (
	find_window,
	capture_window,
	frame_to_base64,
)
from ahu_paimon_toolkit.vlm.client import AsyncVLMClient
from ahu_paimon_toolkit.models import KeyFrame

from shared.config import AppConfig
from shared.input_control import focus_and_click
from shared.llm_client import LLMClient

from orchestrator.context import (
	DecisionHistory,
	DecisionEntry,
	ToolResult,
	build_messages,
	load_game_prompt,
)
from orchestrator.safety import verify_action


# 需要做操作后验证的工具集合
_FUNCTIONAL_TOOLS = {"move"}
# 声明胜利，终止循环
_VICTORY_TOOLS = {"game_victory"}


def _mcp_tools_to_openai(tools: list[McpTool]) -> list[dict]:
	"""将 MCP Tool schema 转为 OpenAI function calling 格式。"""
	result = []
	for t in tools:
		result.append({
			"type": "function",
			"function": {
				"name": t.name,
				"description": t.description or "",
				"parameters": t.inputSchema,
			},
		})
	return result


async def orchestrator_loop(
	config: AppConfig,
	mcp_client: Client,
	vlm_client: AsyncVLMClient,
	llm_client: LLMClient,
) -> None:
	"""Orchestrator 主循环。

	流程: perceive → decide → execute → verify → repeat
	退出条件: game_victory 被调用 / max_iterations 达到 / 连续无操作
	"""
	# 获取可用工具
	mcp_tools = await mcp_client.list_tools()
	openai_tools = _mcp_tools_to_openai(mcp_tools)
	logger.info(f"已注册工具: {[t.name for t in mcp_tools]}")

	# 加载 prompt
	game_prompt = load_game_prompt(config.game.name)
	if not game_prompt:
		logger.warning(f"未找到游戏 prompt: {config.game.name}")

	# 初始化状态
	history = DecisionHistory(max_size=5)
	max_iterations = config.orchestrator.max_iterations
	move_delay_s = config.orchestrator.move_delay_ms / 1000.0
	max_no_action = 3
	no_action_count = 0
	capture_max_size = 1024

	for iteration in range(1, max_iterations + 1):
		logger.info(f"══ 轮次 {iteration}/{max_iterations} ══")

		# ── 1. PERCEIVE ──────────────────────────────────
		focus_and_click(config.game.window_title)
		await asyncio.sleep(0.3)

		try:
			hwnd, title = find_window(config.game.window_title)
			frame = capture_window(hwnd, max_size=capture_max_size)
		except Exception as e:
			logger.error(f"截屏失败: {e}")
			await asyncio.sleep(1.0)
			continue

		b64 = frame_to_base64(frame)
		keyframe = KeyFrame(frame_id=iteration, timestamp_ms=int(time.monotonic() * 1000), base64_image=b64)

		try:
			perception = await vlm_client.describe_frame(keyframe)
			game_state = perception.description
			logger.info(f"VLM 感知: {game_state[:120]}...")
		except Exception as e:
			logger.error(f"VLM 感知失败: {e}")
			await asyncio.sleep(1.0)
			continue

		# ── 2. DECIDE ────────────────────────────────────
		messages = build_messages(
			game_prompt=game_prompt,
			game_state=game_state,
			decision_history=history,
		)

		try:
			response = llm_client.chat_with_tools(
				messages=messages,
				tools=openai_tools,
			)
		except Exception as e:
			logger.error(f"LLM 决策失败: {e}")
			await asyncio.sleep(1.0)
			continue

		if response.content:
			logger.info(f"LLM 思考: {response.content[:120]}")

		if not response.has_tool_calls:
			no_action_count += 1
			logger.warning(f"本轮无工具调用 (连续 {no_action_count}/{max_no_action})")
			if no_action_count >= max_no_action:
				logger.error(f"连续 {max_no_action} 轮无操作，退出")
				break
			continue

		no_action_count = 0

		# ── 3. EXECUTE ───────────────────────────────────
		tool_results: list[ToolResult] = []
		action_names: list[str] = []
		action_args: list[dict] = []
		has_functional = False
		victory = False

		for tc in response.tool_calls:
			logger.info(f"调用工具: {tc.name}({tc.arguments})")
			action_names.append(tc.name)
			action_args.append(tc.arguments)

			if tc.name in _VICTORY_TOOLS:
				try:
					result = await mcp_client.call_tool(tc.name, tc.arguments)
					tool_results.append(ToolResult(name=tc.name, result={"victory": True}))
				except Exception as e:
					tool_results.append(ToolResult(name=tc.name, result={"error": str(e)}))
				logger.info("游戏胜利!")
				victory = True
				break

			try:
				result = await mcp_client.call_tool(tc.name, tc.arguments)
				# 从 CallToolResult 提取文本内容
				result_text = ""
				if result.content:
					for c in result.content:
						if hasattr(c, "text"):
							result_text = c.text
							break
				try:
					result_dict = json.loads(result_text) if result_text else {}
				except (json.JSONDecodeError, TypeError):
					result_dict = {"raw": result_text}
				tool_results.append(ToolResult(name=tc.name, result=result_dict))
				logger.info(f"工具结果: {result_dict}")
			except Exception as e:
				logger.error(f"工具执行失败 {tc.name}: {e}")
				tool_results.append(ToolResult(name=tc.name, result={"error": str(e)}))

			if tc.name in _FUNCTIONAL_TOOLS:
				has_functional = True

		if victory:
			history.add(DecisionEntry(
				iteration=iteration,
				game_state_summary=game_state[:200],
				action_names=action_names,
				action_args=action_args,
				results=tool_results,
				verification="VICTORY",
			))
			break

		# ── 4. VERIFY (仅 functional 操作) ───────────────
		verification: str | None = None
		if has_functional and config.orchestrator.verify_after_action:
			await asyncio.sleep(move_delay_s)

			try:
				verify_frame = capture_window(hwnd, max_size=capture_max_size)
				action_desc = ", ".join(
					f"{n}({a})" for n, a in zip(action_names, action_args)
					if n in _FUNCTIONAL_TOOLS
				)
				verify_result = await verify_action(
					vlm_client, frame, verify_frame, action_desc,
				)
				verification = f"{'SUCCESS' if verify_result.success else 'FAILURE'}: {verify_result.explanation}"
			except Exception as e:
				logger.error(f"验证失败: {e}")
				verification = f"VERIFY_ERROR: {e}"

			logger.info(f"验证: {verification[:100]}")

		# 记录决策历史
		history.add(DecisionEntry(
			iteration=iteration,
			game_state_summary=game_state[:200],
			action_names=action_names,
			action_args=action_args,
			results=tool_results,
			verification=verification,
		))

	logger.info(f"Orchestrator 结束 — 共执行 {len(history)} 轮决策")
