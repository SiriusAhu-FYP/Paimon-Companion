"""统一配置加载 — 从 config.toml + .env 构建 Pydantic 模型。"""

import os
from pathlib import Path

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# 项目根目录 = config.py 所在目录的上一层
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GameConfig(BaseModel):
	name: str = "2048"
	window_title: str = "2048"


class OrchestratorConfig(BaseModel):
	max_iterations: int = 30
	move_delay_ms: int = 150
	verify_after_action: bool = True


class VLMConfig(BaseModel):
	base_url: str = "http://localhost:8000/v1"
	model: str = "Qwen/Qwen2.5-VL-72B-Instruct"


class LLMConfig(BaseModel):
	base_url: str = "https://www.dmxapi.cn/v1/"
	model: str = "gpt-4o"
	temperature: float = 0.3
	api_key: str = ""


class CompanionConfig(BaseModel):
	character: str = "paimon"
	expression_enabled: bool = False


class LoggingConfig(BaseModel):
	level: str = "INFO"
	directory: str = "logs"
	save_screenshots: bool = True


class AppConfig(BaseModel):
	"""顶层配置，聚合所有子模块。"""
	game: GameConfig = Field(default_factory=GameConfig)
	orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
	vlm: VLMConfig = Field(default_factory=VLMConfig)
	llm: LLMConfig = Field(default_factory=LLMConfig)
	companion: CompanionConfig = Field(default_factory=CompanionConfig)
	logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(
	config_path: str | Path | None = None,
	env_path: str | Path | None = None,
) -> AppConfig:
	"""加载配置。

	优先级：.env 环境变量 > config.toml 文件值 > Pydantic 默认值。
	"""
	# 加载 .env（如果存在）
	if env_path is None:
		env_path = _PROJECT_ROOT / ".env"
	load_dotenv(env_path, override=False)

	# 加载 config.toml
	if config_path is None:
		config_path = _PROJECT_ROOT / "config.toml"
	config_path = Path(config_path)

	raw: dict = {}
	if config_path.exists():
		raw = toml.load(config_path)

	# 从环境变量注入 LLM API key（VLM 本地无需认证）
	llm_section = raw.get("llm", {})
	llm_section.setdefault("api_key", os.getenv("LLM_API_KEY", ""))
	raw["llm"] = llm_section

	return AppConfig(**raw)
