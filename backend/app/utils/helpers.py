import string
import random

def generate_random_token(length: int = 12) -> str:
    """
    Generates a random lowercase alpha-numeric string.
    """
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))

def is_text_file(filename: str) -> bool:
    """
    Guesses if a filename represents a standard code/text file based on its extension.
    """
    text_extensions = {
        ".txt", ".md", ".json", ".yaml", ".yml", ".ini", ".cfg",
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
        ".go", ".rs", ".java", ".c", ".cpp", ".h", ".sh", ".sql"
    }
    _, ext = os.path.splitext(filename) if 'os' in globals() else ("", filename.split(".")[-1])
    if ext:
        if not ext.startswith("."):
            ext = "." + ext
        return ext.lower() in text_extensions
    return False
