"""键鼠控制 — 从 LLMPlay-MVP 移植并精简，仅保留 2048 主线所需。"""

import time

from loguru import logger
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

try:
	import win32gui
	import win32con
	_HAS_WIN32 = True
except ImportError:
	_HAS_WIN32 = False


# ---------- singleton controllers ----------

_keyboard: KeyboardController | None = None
_mouse: MouseController | None = None


def _get_keyboard() -> KeyboardController:
	global _keyboard
	if _keyboard is None:
		_keyboard = KeyboardController()
	return _keyboard


def _get_mouse() -> MouseController:
	global _mouse
	if _mouse is None:
		_mouse = MouseController()
	return _mouse


# ---------- key mapping ----------

KEY_MAP: dict[str, Key] = {
	"up": Key.up,
	"down": Key.down,
	"left": Key.left,
	"right": Key.right,
	"enter": Key.enter,
	"space": Key.space,
	"escape": Key.esc,
	"esc": Key.esc,
	"tab": Key.tab,
	"backspace": Key.backspace,
	"delete": Key.delete,
}


# ---------- keyboard ----------

def press_key(key: str) -> str:
	"""按下并释放一个键。返回操作结果描述。"""
	kb = _get_keyboard()
	actual_key = KEY_MAP.get(key.lower(), key.lower())
	try:
		kb.press(actual_key)
		kb.release(actual_key)
		logger.debug(f"Key pressed: {key}")
		return f"Pressed key: {key}"
	except Exception as e:
		logger.error(f"Failed to press key {key}: {e}")
		return f"Error pressing key {key}: {e}"


def press_keys(keys: list[str], delay: float = 0.05) -> str:
	"""按顺序按下多个键。"""
	for key in keys:
		press_key(key)
		if delay > 0:
			time.sleep(delay)
	return f"Pressed {len(keys)} keys"


# ---------- mouse ----------

def mouse_click(x: int, y: int, button: str = "left") -> str:
	"""在指定坐标点击鼠标。"""
	mouse = _get_mouse()
	btn_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
	btn = btn_map.get(button.lower(), Button.left)
	try:
		mouse.position = (x, y)
		mouse.click(btn)
		logger.debug(f"Mouse clicked at ({x}, {y})")
		return f"Clicked at ({x}, {y})"
	except Exception as e:
		logger.error(f"Failed to click at ({x}, {y}): {e}")
		return f"Error clicking at ({x}, {y}): {e}"


# ---------- window focus (Windows only) ----------

def _find_window(title: str) -> int | None:
	"""通过标题模糊匹配查找窗口句柄。"""
	if not _HAS_WIN32:
		logger.warning("win32gui 不可用，无法查找窗口")
		return None

	results: list[int] = []

	def callback(hwnd: int, _: list) -> None:
		if win32gui.IsWindowVisible(hwnd):
			text = win32gui.GetWindowText(hwnd)
			if title.lower() in text.lower():
				results.append(hwnd)

	win32gui.EnumWindows(callback, results)
	return results[0] if results else None


def focus_and_click(title: str) -> bool:
	"""将目标窗口提到前台并点击其中心，确保游戏窗口获得焦点。"""
	if not _HAS_WIN32:
		logger.warning("win32gui 不可用，跳过窗口聚焦")
		return False

	hwnd = _find_window(title)
	if hwnd is None:
		logger.warning(f"未找到窗口: {title}")
		return False

	try:
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
		win32gui.SetForegroundWindow(hwnd)
		time.sleep(0.1)
	except Exception as e:
		logger.error(f"前台切换失败: {e}")
		return False

	# 点击窗口中心
	try:
		left, top, right, bottom = win32gui.GetWindowRect(hwnd)
		cx, cy = (left + right) // 2, (top + bottom) // 2
		mouse = _get_mouse()
		mouse.position = (cx, cy)
		time.sleep(0.05)
		mouse.click(Button.left)
		logger.debug(f"焦点已切换并点击窗口中心 ({cx}, {cy})")
		return True
	except Exception as e:
		logger.error(f"点击窗口中心失败: {e}")
		return False
