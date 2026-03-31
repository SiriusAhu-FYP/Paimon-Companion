# Paimon-Companion

PAIMON = Player-Aware Intelligent Monitoring and Operations Navigator.

A FYP prototype that plays 2048 autonomously using a perceive → decide → execute → verify loop.

## Structure

```
backend/          # Python + FastMCP backend (this is the active prototype)
frontend/         # Live2D companion frontend (planned)
blueprints/      # Phase plans and architecture docs (local only)
dev-reports/     # Run reports and validation logs (local only)
```

## Quick Start

```bash
cd backend
uv sync
cp .env.example .env
# Fill in LLM_API_KEY in .env
uv run python main.py
```

Requirements:
- Python 3.12+
- [vLLM](https://github.com/vllm-project/vllm) running locally for VLM
- A browser open to https://play2048.co/
- LLM API key (DMXAPI or compatible OpenAI-style endpoint)
