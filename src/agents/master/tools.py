from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from src.agents.wiki_reader.wiki_reader import wiki_reader_agent
import uuid

@tool
def wiki_reader_tool(query: str) -> str:
    """
    Ask this tool to gather information from the project Wiki
    :param query: The query to run
    :return: An answer from the wiki
    """
    config = {"thread_id": str(uuid.uuid4())}
    answer = wiki_reader_agent.invoke(
        {"messages": [HumanMessage(query)]}, config=config
    )
    return answer["messages"][-1].content
