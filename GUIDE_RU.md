# Elaira Agent Guide

`Elaira Agent` is an open self-hosted agent repository. You can run it on a VPS, Raspberry Pi, old PC, or another Linux box you control.

## What it is

- A single-folder agent organism
- File-native memory
- Session history in JSONL
- LLM access through OpenRouter-compatible APIs
- Bash as the main universal tool
- Git as its biography and version control

## Why this architecture

- You own the code and can change everything
- You can host it on your own hardware
- You can connect stronger models later, including local models on larger machines
- The agent can improve itself by editing its own repo

## What OpenRouter is

OpenRouter is a unified API gateway for many LLM providers using an OpenAI-compatible format. In practice that means you can swap models without rebuilding the whole agent.

## Typical deployment options

- Cheap Ubuntu VPS
- Raspberry Pi for lightweight remote control and memory
- Old laptop or desktop for personal hosting
- Strong local server with more RAM and a local model stack later

## Install

1. Prepare Ubuntu/Debian server
2. Install `curl` and `git`
3. Run the installer from the repo
4. Set password and API key in `secrets/.env`
5. Open the web UI

## Files that matter

- `memory/` - long-term notes
- `knowledge/` - structured knowledge
- `sessions/active.jsonl` - current session
- `history/` - archived sessions
- `workspace/` - working repos and task files
- `install.sh` - server bootstrap
- `run.sh` - local run helper

## Why it can evolve

The agent reads files, uses tools, changes its own repository, and stores the results in Git. That gives it continuity and a practical surface for growth.

