"""统一决策 LLM 客户端 — 基于 OpenAI SDK，支持 tool_calls。"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion


@dataclass
class ToolCall:
	"""从 LLM 返回的一次 tool call。"""
	id: str
	name: str
	arguments: dict


@dataclass
class LLMResponse:
	"""LLM 调用的结构化结果。"""
	content: str = ""
	tool_calls: list[ToolCall] = field(default_factory=list)
	finish_reason: str = ""

	@property
	def has_tool_calls(self) -> bool:
		return len(self.tool_calls) > 0


class LLMClient:
	"""封装 OpenAI SDK 的决策 LLM 客户端。

	只做最小必要的包装：chat_with_tools → LLMResponse。
	不做流式 UI、不做复杂日志格式、不做图片压缩。
	"""

	def __init__(
		self,
		base_url: str,
		api_key: str,
		model: str,
		temperature: float = 0.3,
	):
		self.model = model
		self.temperature = temperature
		self._client = OpenAI(base_url=base_url, api_key=api_key)

	def chat_with_tools(
		self,
		messages: list[dict],
		tools: list[dict] | None = None,
		temperature: float | None = None,
	) -> LLMResponse:
		"""发送 chat completion 请求，支持 tool_calls。

		Args:
			messages: OpenAI 格式的消息列表。
			tools: OpenAI 格式的工具定义列表（可选）。
			temperature: 覆盖默认温度（可选）。

		Returns:
			LLMResponse，包含 content 和/或 tool_calls。
		"""
		temp = temperature if temperature is not None else self.temperature

		kwargs: dict = {
			"model": self.model,
			"messages": messages,
			"temperature": temp,
		}
		if tools:
			kwargs["tools"] = tools

		try:
			completion: ChatCompletion = self._client.chat.completions.create(**kwargs)
		except Exception as e:
			logger.error(f"LLM 请求失败: {e}")
			raise

		choice = completion.choices[0]
		response = LLMResponse(
			content=choice.message.content or "",
			finish_reason=choice.finish_reason or "",
		)

		# 解析 tool_calls
		if choice.message.tool_calls:
			for tc in choice.message.tool_calls:
				try:
					args = json.loads(tc.function.arguments) if tc.function.arguments else {}
				except json.JSONDecodeError:
					args = {}
					logger.warning(f"tool arguments 解析失败: {tc.function.arguments}")

				response.tool_calls.append(
					ToolCall(id=tc.id, name=tc.function.name, arguments=args)
				)

		logger.info(
			f"LLM 响应: {len(response.content)} chars, "
			f"{len(response.tool_calls)} tool calls, "
			f"finish_reason={response.finish_reason}"
		)
		return response

	def chat(self, messages: list[dict], temperature: float | None = None) -> str:
		"""不带 tools 的简单调用，返回纯文本。"""
		resp = self.chat_with_tools(messages, temperature=temperature)
		return resp.content
