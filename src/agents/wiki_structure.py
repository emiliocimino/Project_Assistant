import os
from pathlib import Path

cwd = Path(os.path.dirname(os.path.abspath(__file__)))
def get_wiki_structure():
    with open(cwd / "wiki_structure.md", "r") as file:
        return file.read()

