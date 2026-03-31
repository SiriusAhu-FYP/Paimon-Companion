"""Paimon-Companion 入口 — 2048 最小闭环。"""

import asyncio
import sys

from loguru import logger

from backend.shared.config import load_config, AppConfig
from backend.shared.llm_client import LLMClient


def setup_logging(cfg: AppConfig) -> None:
	"""配置 loguru。"""
	logger.remove()
	logger.add(
		sys.stderr,
		level=cfg.logging.level,
		format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
	)


def create_llm_client(cfg: AppConfig) -> LLMClient:
	"""根据配置创建 LLM 客户端。"""
	if not cfg.llm.api_key:
		logger.warning("LLM_API_KEY 未设置，LLM 调用将失败")
	return LLMClient(
		base_url=cfg.llm.base_url,
		api_key=cfg.llm.api_key,
		model=cfg.llm.model,
		temperature=cfg.llm.temperature,
	)


def create_vlm_client(cfg: AppConfig):
	"""创建 VLM 客户端（来自 ahu_paimon_toolkit）。

	本地 vLLM 服务无需认证，直接使用原生 AsyncVLMClient。
	"""
	from ahu_paimon_toolkit.vlm.client import AsyncVLMClient
	return AsyncVLMClient(
		base_url=cfg.vlm.base_url,
		model=cfg.vlm.model,
	)


async def run() -> None:
	cfg = load_config()
	setup_logging(cfg)
	logger.info(f"配置已加载 — 游戏: {cfg.game.name}, LLM: {cfg.llm.model}, VLM: {cfg.vlm.model}")

	# LLM 客户端（决策）
	llm_client = create_llm_client(cfg)

	# VLM 客户端（感知 + 验证）
	vlm_client = create_vlm_client(cfg)
	logger.info(f"VLM 客户端已创建: {cfg.vlm.model} @ {cfg.vlm.base_url}")

	# FastMCP server + plugin 注册
	from fastmcp import FastMCP, Client
	from backend.plugins import register_all_plugins

	server = FastMCP("paimon-companion")
	register_all_plugins(
		server,
		cfg.game.name,
		window_title=cfg.game.window_title,
		move_delay_ms=cfg.orchestrator.move_delay_ms,
	)
	logger.info("FastMCP server 已创建，插件已注册")

	# Orchestrator 主循环
	from backend.orchestrator.loop import orchestrator_loop

	async with Client(server) as mcp_client:
		logger.info("MCP in-process 连接已建立，启动 Orchestrator")
		await orchestrator_loop(cfg, mcp_client, vlm_client, llm_client)

	# 清理
	await vlm_client.close()
	logger.info("已退出")


def main() -> None:
	asyncio.run(run())


if __name__ == "__main__":
	main()
