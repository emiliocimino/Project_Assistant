import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware
from langchain_openai import ChatOpenAI

from src import WIKI_DIR
from src.agents.mcp import get_filtered_tools
from src.agents.middlewares import LogToolUsage, TolerateToolErrors
from src.agents.wiki_reader.system_prompt import get_system_prompt

load_dotenv(override=True)
MODEL_NAME = os.getenv("MODEL_NAME")
URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

MAX_ATTEMPTS = 3
MODEL = ChatOpenAI(model=MODEL_NAME, base_url=URL, api_key=API_KEY)

tool_list = [
        "read_text_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "list_allowed_directories",
]

wiki_reader_agent = create_agent(
    model=MODEL,
    system_prompt=get_system_prompt(),
    tools=asyncio.run(get_filtered_tools(str(WIKI_DIR), tool_list)),
    middleware=[
        TodoListMiddleware(),
        ModelCallLimitMiddleware(run_limit=20),
        LogToolUsage("Wiki Reader"),
        TolerateToolErrors(),
    ],
)
