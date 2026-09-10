import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import

from src import DATA_DIR
from src.agents.mcp import get_filtered_tools
from src.agents.middlewares import LogToolUsage, OverwriteGuardrail, TolerateToolErrors
from src.agents.source_manager.system_prompt import BASE_SYSTEM_PROMPT

load_dotenv(override=True)
MODEL_NAME = os.getenv("MODEL_NAME")
URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

MAX_ATTEMPTS = 3
MODEL = ChatOpenAI(model=MODEL_NAME, base_url=URL, api_key=API_KEY)


source_manager_agent = create_agent(
    model=MODEL,
    system_prompt=BASE_SYSTEM_PROMPT,
    tools=asyncio.run(get_filtered_tools(str(DATA_DIR))),
    middleware=[
        TodoListMiddleware(),
        OverwriteGuardrail(str(DATA_DIR)),
        LogToolUsage("Source Manager"),
        TolerateToolErrors(),
    ],
)