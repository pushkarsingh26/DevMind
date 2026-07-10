import os
import json
from typing import List, Dict, Any

_current_dir = os.path.dirname(os.path.abspath(__file__))
_templates_path = os.path.join(_current_dir, "workflow_templates.json")

try:
    with open(_templates_path, "r", encoding="utf-8") as f:
        WORKFLOW_TEMPLATES: Dict[str, List[Dict[str, Any]]] = json.load(f)
except Exception as e:
    print(f"Error loading workflow templates: {e}")
    WORKFLOW_TEMPLATES = {}
