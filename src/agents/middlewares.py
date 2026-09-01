import os

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

    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        logger.info(f"Used tool: {tool_call["name"]} with args: {tool_call["args"]}")
        return await handler(request)


class ImageToolGuardrail(AgentMiddleware):
    """Avoids use of images for OCR"""

    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        if tool_call["name"] == "pdf_evidence":
            if tool_call["args"]["operation"] == "render_page":
                logger.info("[Middleware Guardrail]: Skipping Image tool")
                return ToolMessage(
                    content=f"Rendering Tool is forbidden. Please use other tools that does not involve images",
                    tool_call_id=request.tool_call["id"],
                )
        return await handler(request)


class OverwriteGuardrail(AgentMiddleware):
    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        name = tool_call["name"]
        args = tool_call["args"]

        if name == "create_folder":
            path = args.get("path")  # confirm this is the real key from your debug log
            if path and os.path.isdir(path):
                logger.info(f"[OverwriteGuardrail] folder already exists: {path}")
                return ToolMessage(
                    content=f"Folder {path} already exists. No need to create it again.",
                    tool_call_id=tool_call["id"],
                )

        elif name == "write_file":
            path = args.get("path")
            if path and os.path.isfile(path):
                logger.info(f"[OverwriteGuardrail] file exists, redirecting to edit_file: {path}")
                return ToolMessage(
                    content=f"File {path} already exists. Use edit_file to update it "
                            f"instead of write_file, to avoid overwriting existing content.",
                    tool_call_id=tool_call["id"],
                )

        return await handler(request)
