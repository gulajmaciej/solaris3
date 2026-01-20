# Solaris3 Prototype

Solaris3 is a turn-based simulation prototype with two AI agents (instrument specialist and crew officer) operating a remote station above Solaris.

## Requirements

- Python 3.11+ (tested with 3.12)
- Ollama (only required for LLM or hybrid decision modes)

## Install

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Install Ollama And The Local Model

1) Install Ollama from `https://ollama.com/`
2) Pull the default model used by Solaris3:

```
ollama pull qwen2.5:7b
```

You can override the model name with:

```
setx OLLAMA_MODEL "qwen2.5:7b"
```

Restart your terminal after setting the variable.

## Run

TUI (default):

```
python -m game
```

CLI:

```
python -m game --cli
```

## Decision Modes (CLI Arguments)

Use `--decision-mode` to control agent tool selection:

- `deterministic`: rules-based tool selection only
- `llm`: LLM-only tool selection (Ollama required)
- `hybrid`: deterministic unless confidence/conditions trigger LLM (Ollama required)

Example:

```
python -m game --cli --decision-mode hybrid
```

## Data Storage

Runs are stored as TinyDB JSON files under `data/`:

- `data/run_<run_id>.json`

## GameState Fields

- tension
- ocean_activity
- crew_load
- earth_pressure
- station_power
- turn

## Docs

- Instrument Specialist: `docs/instrument_specialist.md`
- Crew Officer: `docs/crew_officer.md`
