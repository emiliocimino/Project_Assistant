from langchain_mcp_adapters.client import MultiServerMCPClient


def mcp_connections(sandbox: str) -> dict:
    """The MCP servers the Sidekick uses: a headed browser and a sandbox filesystem."""
    return {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox],
        },
    }


async def get_tools(sandbox: str):
    client = MultiServerMCPClient(mcp_connections(sandbox))
    browser_tools = await client.get_tools()
    tool_list = [
        "read_text_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "list_allowed_directories",
    ]
    allowed_tools = [t for t in browser_tools if t.name in tool_list]

    return allowed_tools


if __name__ == "__main__":
    import asyncio

    tools = asyncio.run(get_tools(sandbox="."))
    print(tools)
