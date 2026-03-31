"""决策上下文管理 — DecisionHistory + build_messages。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolResult:
	"""单个工具调用的结果。"""
	name: str
	result: dict


@dataclass
class DecisionEntry:
	"""单次决策记录。"""
	iteration: int
	game_state_summary: str
	action_names: list[str]
	action_args: list[dict]
	results: list[ToolResult]
	verification: str | None = None
	timestamp: float = field(default_factory=time.monotonic)


class DecisionHistory:
	"""维护最近 N 轮的决策记录。"""

	def __init__(self, max_size: int = 5) -> None:
		self._max_size = max_size
		self._entries: list[DecisionEntry] = []

	def add(self, entry: DecisionEntry) -> None:
		self._entries.append(entry)
		if len(self._entries) > self._max_size:
			self._entries = self._entries[-self._max_size:]

	def to_text(self) -> str:
		"""格式化为 LLM 可读的文本摘要。"""
		if not self._entries:
			return "No previous actions."

		lines: list[str] = []
		for e in self._entries:
			actions = ", ".join(
				f"{name}({args})"
				for name, args in zip(e.action_names, e.action_args)
			)
			verify = f" → {e.verification}" if e.verification else ""
			lines.append(
				f"Round {e.iteration}: {actions}{verify}"
			)
		return "\n".join(lines)

	def clear(self) -> None:
		self._entries.clear()

	@property
	def entries(self) -> list[DecisionEntry]:
		return list(self._entries)

	def __len__(self) -> int:
		return len(self._entries)


def _load_prompt_file(path: Path) -> str:
	"""加载 prompt 文件，不存在则返回空字符串。"""
	if path.exists():
		return path.read_text(encoding="utf-8").strip()
	return ""


def load_game_prompt(game: str, prompts_dir: Path | None = None) -> str:
	"""加载游戏专用 prompt。"""
	if prompts_dir is None:
		prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
	return _load_prompt_file(prompts_dir / "games" / f"{game}.md")


def build_messages(
	game_prompt: str,
	game_state: str,
	decision_history: DecisionHistory,
) -> list[dict]:
	"""构建发给决策 LLM 的 messages 数组。

	结构:
	  [0] system: 角色身份 + 游戏规则
	  [1] user: 当前游戏状态 + 历史决策摘要
	"""
	system_content = (
		"You are PAIMON, an AI game assistant. "
		"Analyze the game state and choose the best action using the available tools.\n\n"
		f"{game_prompt}"
	)

	history_text = decision_history.to_text()
	user_content = (
		f"## Current Game State\n\n{game_state}\n\n"
		f"## Previous Actions\n\n{history_text}\n\n"
		"Based on the current game state and previous actions, decide your next move. "
		"Call the appropriate tool to execute your decision."
	)

	return [
		{"role": "system", "content": system_content},
		{"role": "user", "content": user_content},
	]
