from langchain_core.tools import tool

from src import WIKI_DIR


@tool
def append_to_log(entry: str):
    """
    Appends entry to the /wiki/log.md file (safer than edit file)
    :param entry: log entry
    """
    with open(WIKI_DIR / "log.md", "a") as f:
        f.write(entry + "\n")
        return f"Written {entry} to /wiki/log.md"
