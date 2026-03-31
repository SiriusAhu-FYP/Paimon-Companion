"""2048 游戏 MCP 工具 — 唯一操作接口 move(direction)。"""

import time

from fastmcp import FastMCP
from loguru import logger

from backend.shared.input_control import press_key, focus_and_click


# 允许的方向值
_VALID_DIRECTIONS = {"up", "down", "left", "right"}


def register(server: FastMCP, *, window_title: str = "2048", move_delay_ms: int = 150) -> None:
	"""将 2048 工具注册到 FastMCP server。"""

	@server.tool(
		description=(
			"Press a direction key in the 2048 game. "
			"direction must be one of: up, down, left, right."
		),
	)
	def move(direction: str) -> dict:
		d = direction.lower().strip()
		if d not in _VALID_DIRECTIONS:
			logger.warning(f"无效方向: {direction}")
			return {"success": False, "error": f"Invalid direction: {direction}. Must be one of: up, down, left, right."}

		focus_and_click(window_title)
		time.sleep(0.05)
		result = press_key(d)
		time.sleep(move_delay_ms / 1000.0)
		logger.info(f"2048 move: {d}")
		return {"success": True, "direction": d, "result": result}

	@server.tool(
		description="Declare game victory when you see a 2048 tile or 'You Win' message.",
	)
	def game_victory() -> dict:
		logger.info("2048: 游戏胜利宣告")
		return {"success": True, "message": "Victory declared!"}
