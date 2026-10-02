import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_openai import ChatOpenAI

from src import DATA_DIR
from src.agents.custom_tools import append_to_log
from src.agents.mcp import get_filtered_tools
from src.agents.middlewares import (
    LogToolUsage,
    OverwriteGuardrail,
    SafeguardRepetitiveCalls,
    TolerateToolErrors,
)
from src.agents.source_manager.system_prompt import get_system_prompt

load_dotenv(override=True)
MODEL_NAME = os.getenv("MODEL_NAME")
URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

MAX_ATTEMPTS = 3
MODEL = ChatOpenAI(model=MODEL_NAME, base_url=URL, api_key=API_KEY)

tool_list = asyncio.run(get_filtered_tools(str(DATA_DIR)))
tool_list.append(append_to_log)

source_manager_agent = create_agent(
    model=MODEL,
    system_prompt=get_system_prompt(),
    tools=tool_list,
    middleware=[
        TodoListMiddleware(),
        OverwriteGuardrail(str(DATA_DIR)),
        SafeguardRepetitiveCalls(),
        LogToolUsage("Source Manager"),
        TolerateToolErrors(),
    ],
)