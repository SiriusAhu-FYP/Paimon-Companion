"""插件注册入口。"""

from fastmcp import FastMCP


def register_all_plugins(
	server: FastMCP,
	game: str,
	*,
	window_title: str = "2048",
	move_delay_ms: int = 150,
) -> None:
	"""根据游戏名注册对应的 game plugin。"""
	if game == "2048":
		from backend.plugins.games.game_2048 import register
		register(server, window_title=window_title, move_delay_ms=move_delay_ms)
	else:
		raise ValueError(f"未知游戏: {game}")
