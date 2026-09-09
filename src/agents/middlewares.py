import os
from pathlib import Path

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from loguru import logger


class TolerateToolErrors(AgentMiddleware):
    """Hand tool failures back to the model as a message so it can recover, rather than
    crashing the run. Tools that touch the outside world, like a browser, fail now and then."""

    async def awrap_tool_call(self, request, handler):
        try:
            return await handler(request)
        except Exception as error:
            logger.error(f"Tool call failed: {error}. Try another approach.")
            return ToolMessage(
                content=f"That tool call failed: {error}. Try another approach.",
                tool_call_id=request.tool_call["id"],
            )


class LogToolUsage(AgentMiddleware):
    """Log tool usage"""
    def __init__(self, model_name):
        self.model_name = model_name

    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        logger.info(f"{self.model_name} used tool: {tool_call['name']} with args: {tool_call['args']}")
        return await handler(request)



class OverwriteGuardrail(AgentMiddleware):
    def __init__(self, sandbox: str | Path):
        self.sandbox = Path(sandbox).resolve()

    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        name = tool_call["name"]
        args = tool_call["args"]

        path = args.get("path")
        if path:
            path = resolve_path(path, self.sandbox)

        if name == "create_folder":
            if os.path.isdir(path):
                logger.info(f"[OverwriteGuardrail] folder already exists: {path}")
                return ToolMessage(
                    content=f"Folder {path} already exists. No need to create it again.",
                    tool_call_id=tool_call["id"],
                )

        elif name == "write_file":
            if os.path.isfile(path):
                logger.info(
                    f"[OverwriteGuardrail] file exists, redirecting to edit_file: {path}"
                )
                return ToolMessage(
                    content=f"File {path} already exists. Use edit_file to update it "
                    f"instead of write_file, to avoid overwriting existing content.",
                    tool_call_id=tool_call["id"],
                )

        return await handler(request)



def resolve_path(path: str, sandbox: Path) -> Path:
    path = Path(path)

    if path.is_absolute():
        return path.resolve()

    return (sandbox / path).resolve()
