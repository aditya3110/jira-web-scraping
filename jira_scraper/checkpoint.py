import json
import os
import tempfile
from typing import Any, Dict


DEFAULT_STATE: Dict[str, Any] = {"projects": {}}


def load_state(state_path: str) -> Dict[str, Any]:
    if not os.path.exists(state_path):
        return {"projects": {}}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "projects" not in data:
            return {"projects": {}}
        return data
    except Exception:
        # Corrupt or unreadable; start fresh but do not overwrite immediately
        return {"projects": {}}


def save_state(state_path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="state.", suffix=".json", dir=os.path.dirname(state_path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, state_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def get_project_state(state: Dict[str, Any], project_key: str) -> Dict[str, Any]:
    return state.setdefault("projects", {}).setdefault(project_key, {"start_at": 0, "done": False})


def update_project_state(state: Dict[str, Any], project_key: str, **kwargs: Any) -> None:
    project_state = get_project_state(state, project_key)
    project_state.update(kwargs)


