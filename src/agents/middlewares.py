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
        if tool_call["name"] in ("create_folder", "write_file"):
            logger.debug(f"[OverwriteGuardrail] tool={tool_call['name']} args={tool_call['args']}")
            enquired_path = tool_call["args"].get("path")
            if enquired_path and os.path.exists(enquired_path):
                logger.info(f"[Middleware Guardrail]: {enquired_path} already exists")
                return ToolMessage(
                    content=f"File or Folder {enquired_path} already exists. Do not call {tool_call['name']} with path {tool_call['args']['path']} anymore.",
                    tool_call_id=request.tool_call["id"],
                )
        return await handler(request)
