# Frontend

> VoiceL2D companion frontend (Live2D + TTS + ASR integration point).
> This directory will host the companion-facing UI layer.

## Current Status

Frontend integration is not yet connected. In Phase 1, the companion loop runs
in headless mode via `backend/main.py`.

## Future Integration

When a frontend is added, it will communicate with the backend via:

- **WebSocket / SSE** for real-time expression and character events
- **HTTP API** for command dispatching (e.g., `express(emotion)`, `speak(text)`)
- See `blueprints/phase0/architecture/orchestrator-design.md` for the intended
  communication architecture.

## Directory Structure (planned)

```
frontend/
├── public/          # Static assets
├── src/             # Frontend source (React / PIXI / Cubism4)
├── api/             # Backend API client
└── README.md        # This file
```
