"""轻量操作后验证 — 基于 VLM 前后截图比对。"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger

from ahu_paimon_toolkit.vlm.client import AsyncVLMClient

if __name__ != "__main__":
	from numpy.typing import NDArray


@dataclass
class VerifyResult:
	success: bool
	explanation: str


def _frame_to_base64(frame: NDArray[np.uint8], quality: int = 85) -> str:
	"""将 BGR numpy 数组编码为 JPEG base64 字符串。"""
	encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
	ok, buf = cv2.imencode(".jpg", frame, encode_params)
	if not ok:
		raise RuntimeError("JPEG 编码失败")
	return base64.b64encode(buf.tobytes()).decode("ascii")


async def verify_action(
	vlm_client: AsyncVLMClient,
	frame_before: NDArray[np.uint8],
	frame_after: NDArray[np.uint8],
	action_description: str,
) -> VerifyResult:
	"""通过 VLM 比对操作前后截图，判断操作是否成功。

	向 VLM 发送两张图片和操作描述，要求回答 SUCCESS 或 FAILURE。
	"""
	b64_before = _frame_to_base64(frame_before)
	b64_after = _frame_to_base64(frame_after)

	prompt = (
		f"Compare these two game screenshots. The action performed was: {action_description}.\n"
		"Determine if the action was successfully executed by checking if the game state changed.\n"
		"Reply with exactly one word on the first line: SUCCESS or FAILURE.\n"
		"Then on the next line, briefly explain why."
	)

	messages = [
		{
			"role": "user",
			"content": [
				{"type": "text", "text": prompt},
				{
					"type": "image_url",
					"image_url": {"url": f"data:image/jpeg;base64,{b64_before}"},
				},
				{
					"type": "image_url",
					"image_url": {"url": f"data:image/jpeg;base64,{b64_after}"},
				},
			],
		}
	]

	try:
		response_text = await vlm_client.chat(messages)
		lines = response_text.strip().split("\n", 1)
		verdict = lines[0].strip().upper()
		explanation = lines[1].strip() if len(lines) > 1 else ""

		success = "SUCCESS" in verdict
		logger.info(f"验证结果: {'SUCCESS' if success else 'FAILURE'} — {explanation[:80]}")
		return VerifyResult(success=success, explanation=explanation)

	except Exception as e:
		logger.error(f"验证请求失败: {e}")
		return VerifyResult(success=False, explanation=f"Verification failed: {e}")
