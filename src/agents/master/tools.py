import uuid

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from src.agents.source_manager.source_manager import source_manager_agent
from src.agents.wiki_reader.wiki_reader import wiki_reader_agent


@tool
async def wiki_reader_tool(query: str) -> str:
    """
    Ask this tool to gather information from the project Wiki
    :param query: The query to run
    :return: An answer from the wiki
    """
    answer = await wiki_reader_agent.ainvoke(
        {"messages": [HumanMessage(query)]},
    )
    return answer["messages"][-1].content


@tool
async def source_manager_tool(query: str, file_paths: list[str]) -> str:
    """
    Ask this tool to update information from the project Wiki
    :param query: A piece of information to send if any, otherwise a '' string
    :param file_paths: A list of file paths (if they exist), otherwise empty list
    :return: Summary of updated information
    """
    built_message = f"""Update the wiki with the following information : {query}.\n\n A list of filepath is here {"\n".join(file_paths)}"""
    answer = await source_manager_agent.ainvoke(
        {"messages": [HumanMessage(built_message)]}
    )
    return answer["messages"][-1].content


tools = [source_manager_tool, wiki_reader_tool]

def get_tools():
    return tools