import json
import re
from typing import Dict, Any
from app.core.logger import logger

def repair_parentheses(text: str) -> str:
    """
    Scans the text and attempts to repair truncated JSON structure by:
    1. Closing any open double quotes (while correctly handling escape sequences).
    2. Appending closing brackets and braces in the correct reverse order of opening them.
    3. Stripping trailing commas that could cause syntax errors prior to closing brackets.
    """
    text = text.strip()
    in_string = False
    escape = False
    stack = []
    
    for char in text:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char in ('}', ']'):
                if stack and stack[-1] == char:
                    stack.pop()
                    
    repaired = text
    if in_string:
        # If there is a trailing escape character, strip it first
        if text.endswith('\\') and not text.endswith('\\\\'):
            repaired = repaired[:-1]
        repaired += '"'
        
    repaired_stripped = repaired.rstrip()
    if repaired_stripped.endswith(','):
        repaired = repaired_stripped[:-1]
        
    while stack:
        repaired += stack.pop()
        
    return repaired

def parse_repaired_json(text: str) -> Dict[str, Any]:
    """
    Attempts to parse JSON from potentially truncated or malformed text.
    Uses backtracking to truncate the string at each comma character outside
    of string literals, applies parenthesis repair, and checks if it parses successfully.
    """
    text = text.strip()
    if not text:
        return {}
        
    # First: Try standard repair of parentheses
    repaired = repair_parentheses(text)
    try:
        result = json.loads(repaired)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
        
    # Second: If first attempt fails, find comma locations outside of strings
    comma_positions = []
    in_string = False
    escape = False
    for idx, char in enumerate(text):
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if char == ',' and not in_string:
            comma_positions.append(idx)
            
    # Iterate backwards through comma positions to find a clean prefix to repair
    for comma_idx in reversed(comma_positions):
        truncated = text[:comma_idx]
        repaired = repair_parentheses(truncated)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
            
    # Raise parsing error if all repair attempts fail
    raise ValueError("JSON repair backtrack exhausted all comma delimiters without success.")
