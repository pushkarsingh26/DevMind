import os
import json
from typing import List, Dict, Any, Optional

# Place data directory in backend/data/workflows
DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "workflows"))

def get_workflow_dir(workflow_id: str) -> str:
    path = os.path.join(DATA_ROOT, workflow_id)
    os.makedirs(path, exist_ok=True)
    return path

def append_log(workflow_id: str, log_entry: Dict[str, Any]):
    wdir = get_workflow_dir(workflow_id)
    log_file = os.path.join(wdir, "logs.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, default=str) + "\n")

def write_all_logs(workflow_id: str, logs: List[Dict[str, Any]]):
    wdir = get_workflow_dir(workflow_id)
    log_file = os.path.join(wdir, "logs.jsonl")
    with open(log_file, "w", encoding="utf-8") as f:
        for log in logs:
            f.write(json.dumps(log, default=str) + "\n")

def read_logs(workflow_id: str) -> List[Dict[str, Any]]:
    wdir = get_workflow_dir(workflow_id)
    log_file = os.path.join(wdir, "logs.jsonl")
    if not os.path.exists(log_file):
        return []
    logs = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    logs.append(json.loads(line.strip()))
                except Exception:
                    pass
    return logs

def save_json(workflow_id: str, filename: str, data: Any) -> str:
    wdir = get_workflow_dir(workflow_id)
    file_path = os.path.join(wdir, filename)
    temp_path = file_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(temp_path, file_path)
    return file_path

def load_json(workflow_id: str, filename: str) -> Optional[Any]:
    wdir = get_workflow_dir(workflow_id)
    file_path = os.path.join(wdir, filename)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_text(workflow_id: str, filename: str, content: str) -> str:
    wdir = get_workflow_dir(workflow_id)
    file_path = os.path.join(wdir, filename)
    temp_path = file_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(temp_path, file_path)
    return file_path

def load_text(workflow_id: str, filename: str) -> Optional[str]:
    wdir = get_workflow_dir(workflow_id)
    file_path = os.path.join(wdir, filename)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None
