from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from contextlib import AsyncExitStack
from pydantic import BaseModel, Field

class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(
        description="True if the assistant has a question, needs clarification, or is stuck and needs the user"
    )

def mcp_connections(sandbox: str) -> dict:
    """The MCP servers the Sidekick uses: a headed browser and a sandbox filesystem."""
    return {
        "citra": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@sylphx/citra"],
        },
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox],
        },
    }

class McpSessions:
    """Holds persistent MCP sessions open so the browser keeps its state between tool calls.

    The stdio transport must be opened and closed from the same asyncio task, so one
    background task owns the sessions: it opens them, waits, and unwinds them when stop()
    is called. Stopping shuts down the servers, and you will see the browser close.
    """

    def __init__(self, connections: dict):
        self.connections = connections
        self.tools = []
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._task = None

    async def _run(self):
        client = MultiServerMCPClient(self.connections)
        async with AsyncExitStack() as stack:
            for name in self.connections:
                session = await stack.enter_async_context(client.session(name))
                self.tools += await load_mcp_tools(session, server_name=name)
            self._ready.set()
            await self._stop.wait()

    async def start(self) -> list:
        self._task = asyncio.create_task(self._run())
        ready = asyncio.create_task(self._ready.wait())
        await asyncio.wait([ready, self._task], return_when=asyncio.FIRST_COMPLETED)
        ready.cancel()
        if self._task.done():
            self._task.result()  # the servers failed to start; raise the real error
        return self.tools

    def stop(self):
        self._stop.set()


async def get_tools(sandbox: str):
    """Return the full tool list (our tools plus the MCP server tools) and the session holder."""
    sessions = McpSessions(mcp_connections(sandbox))
    mcp_tools = await sessions.start()
    return mcp_tools, sessions



if __name__ == "__main__":
    import asyncio

    client = MultiServerMCPClient(mcp_connections("test"))
    browser_tools = asyncio.run(client.get_tools())
    print(f"Loaded {len(browser_tools)} browser tools:")
    for t in browser_tools:
        print(" -", t.name)