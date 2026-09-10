import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = BASE_DIR / "data"
WIKI_DIR = DATA_DIR / "wiki"
SOURCE_DIR = DATA_DIR / "source"
MEMORY_DIR = BASE_DIR / "conversations"
