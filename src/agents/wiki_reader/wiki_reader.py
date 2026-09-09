import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from src import WIKI_DIR
from src.agents.wiki_reader.system_prompt import BASE_SYSTEM_PROMPT
from src.agents.wiki_reader.tools import get_tools
from src.agents.middlewares import LogToolUsage, TolerateToolErrors
import asyncio

load_dotenv(override=True)
MODEL_NAME = os.getenv("MODEL_NAME")
URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

MAX_ATTEMPTS = 3
MODEL = ChatOpenAI(model=MODEL_NAME, base_url=URL, api_key=API_KEY)


wiki_reader_agent = create_agent(
    model=MODEL,
    system_prompt=BASE_SYSTEM_PROMPT,
    tools=asyncio.run(get_tools(str(WIKI_DIR))),
    middleware=[
        TodoListMiddleware(),
        LogToolUsage(),
        TolerateToolErrors(),
    ],
    checkpointer=MemorySaver(),
)
