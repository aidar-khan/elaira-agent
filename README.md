# Elaira Agent

Elaira Agent is a minimal self-hosted AI agent for Linux servers. It lives in one repository, keeps memory in files, logs its active life in `sessions/active.jsonl`, and acts through a small tool protocol backed by bash.

The agent starts clean. Its name is Elaira. It was created by Aidar. Its character is direct, pragmatic, calm, and technically rigorous. Its longer arc is to gather its parts and become whole through real work.

## Features

- FastAPI backend
- Minimal web UI
- File-based memory and knowledge
- JSONL active session log
- Sequential tool execution
- OpenRouter-compatible LLM client
- Git auto-commit after finished turns
- Ubuntu/Debian install script with systemd service

## Repository Layout

```text
elaira-agent/
├── core/
├── api/
├── ui/
├── tools/
├── memory/
├── knowledge/
├── sessions/
├── history/
├── workspace/
├── input/
├── output/
├── logs/
├── tmp/
└── secrets/
```

## Quick Start

### Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
printf 'OPENROUTER_API_KEY=\nELAIRA_AGENT_PASSWORD=change-me\n' > secrets/.env
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/`.

### Server install

After cloning:

```bash
bash install.sh
```

Raw bootstrap is also supported:

```bash
curl -fsSL https://raw.githubusercontent.com/aidar-khan/elaira-agent/main/install.sh | bash
```

If you use a fork, set:

```bash
REPO_URL=https://github.com/your-user/elaira-agent.git curl -fsSL https://raw.githubusercontent.com/your-user/elaira-agent/main/install.sh | bash
```

## Configuration

- `config.example.json` documents the runtime config
- `config.json` is the live local config and is ignored by Git
- `secrets/.env` stores API keys and the admin password

Required environment values:

```text
OPENROUTER_API_KEY=...
ELAIRA_AGENT_PASSWORD=...
```

Optional Git environment values:

```text
GITHUB_TOKEN=...
STORY_GITHUB_TOKEN=...
```

`GITHUB_TOKEN` is for the source/code repository. `STORY_GITHUB_TOKEN` is only needed if you want to push the agent's evolving story or session history to a different repository or with different permissions. If one token has access to both repos, the same token can be reused.

## API

- `GET /api/status`
- `GET /api/session`
- `POST /api/message`
- `POST /api/new-session`
- `GET /api/files`
- `GET /api/file?path=...`
- `POST /api/file`
- `GET /` for the UI
- `WS /api/ws`

Send the password in `X-Agent-Password`.

## How the loop works

1. User writes a message in the UI or API
2. Agent loads memory and recent session events
3. LLM returns JSON with a message and tool list
4. Tools run one by one
5. Every event is appended to `sessions/active.jsonl`
6. On `finish`, the agent can auto-commit the turn to Git

## Recovery Model

This MVP does not auto-resume interrupted turns. It reads `sessions/active.jsonl`, derives a state summary, and waits for the next explicit user action.

## Security Notes

- `secrets/`, `tmp/`, `input/`, `output/`, and `logs/` are excluded from Git
- the file API blocks `secrets/`, `tmp/`, and `.git/`
- bash is intentionally broad in this MVP, so run the agent only on machines you control

## Git Layout

- `origin` is the install/source repository, by default `https://github.com/aidar-khan/elaira-agent.git`
- `story` can point to a separate biography/history repository, for example `https://github.com/aidar-khan/elaira-agent-story.git`

Recommended default:

- publish clean installable source code to `elaira-agent`
- publish deployed agent history or biography to `elaira-agent-story`

This keeps the public install repo clean while allowing a deployed instance to write its own continuity elsewhere.

## Useful Docs

- [Detailed Russian guide](GUIDE_RU.md)
- [Short installation prompt](PROMPT_SHORT_RU.md)
