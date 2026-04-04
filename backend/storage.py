import json
from pathlib import Path


STATE_FILE = Path(__file__).resolve().parent / "archivos_datos" / "backend_state.json"


def load_state(default_state):
    state = dict(default_state)

    if not STATE_FILE.exists():
        return state

    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state

    if not isinstance(payload, dict):
        return state

    for key, default_value in default_state.items():
        value = payload.get(key, default_value)

        if isinstance(default_value, list) and isinstance(value, list):
            state[key] = value
        elif isinstance(default_value, dict) and isinstance(value, dict):
            state[key] = value
        elif isinstance(default_value, str) and isinstance(value, str):
            state[key] = value
        else:
            state[key] = default_value

    return state


def save_state(state, default_state):
    serializable_state = {}

    for key, default_value in default_state.items():
        value = state.get(key, default_value)

        if isinstance(default_value, list) and isinstance(value, list):
            serializable_state[key] = value
        elif isinstance(default_value, dict) and isinstance(value, dict):
            serializable_state[key] = value
        elif isinstance(default_value, str) and isinstance(value, str):
            serializable_state[key] = value
        else:
            serializable_state[key] = default_value

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(serializable_state, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
