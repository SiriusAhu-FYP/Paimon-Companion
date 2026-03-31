# Paimon-Companion

PAIMON = Player-Aware Intelligent Monitoring and Operations Navigator.

A FYP prototype that plays 2048 autonomously using a perceive → decide → execute → verify loop.

## Structure

```
backend/          # Python + FastMCP backend (orchestrator, plugins, shared modules)
frontend/         # Live2D companion frontend (VoiceL2D-based, pnpm + Vite)
blueprints/       # Phase plans and architecture docs (local only)
dev-reports/      # Run reports and validation logs (local only)
ahu_paimon_toolkit/  # Local copy of ahu_paimon_toolkit (not tracked in git)
```

## Quick Start

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# Fill in LLM_API_KEY in .env
uv run python main.py
```

Or from repo root with explicit module invocation:

```bash
uv sync
cp backend/.env.example .env
# Fill in LLM_API_KEY in .env
uv run python -m backend.main
```

Requirements:
- Python 3.12+
- [vLLM](https://github.com/vllm-project/vllm) running locally for VLM (port 8000)
- A browser open to https://play2048.co/
- LLM API key (DMXAPI or compatible OpenAI-style endpoint)

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Requirements:
- Node.js 18+
- pnpm 8+
