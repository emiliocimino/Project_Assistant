from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    TodoListMiddleware)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
import aiosqlite
import os
from dotenv import load_dotenv

from src.agents.master.system_prompt import BASE_SYSTEM_PROMPT
from src.agents.middlewares import TolerateToolErrors, LogToolUsage, ImageToolGuardrail, OverwriteGuardrail
from src.memory.manager import get_sqlite_connection
from src.agents.tools import get_tools, McpSessions, EvaluatorOutput
from src import DATA_DIR

load_dotenv(override=True)
MODEL_NAME = os.getenv("MODEL_NAME")
URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

MAX_ATTEMPTS = 3


class WikiAgent:
    def __init__(self,
                 conn: aiosqlite.Connection,
                 checkpointer: AsyncSqliteSaver,
                 graph: CompiledStateGraph,
                 thread_id: str,
                 tools: list[dict],
                 sessions: McpSessions
                 ):
        self._conn = conn
        self._checkpointer = checkpointer
        self._graph = graph
        self.thread_id = thread_id
        self.tools = tools
        self._sessions = sessions
        self._evaluator = None
        self.task = None
        self.success_criteria = None
        self.todos = []
        self.evaluator = ChatOpenAI(
            model=MODEL_NAME,
            base_url=URL,
            api_key=API_KEY
        ).with_structured_output(EvaluatorOutput)

    @classmethod
    async def setup(cls, thread_id: str):
        """thread_id can be a brand new uuid4 (new conversation) or an id recovered
        from list_threads() below (resuming a past one). Either way this just binds
        a fresh graph/agent to that thread_id; AsyncSqliteSaver picks up wherever
        that thread's checkpoint history left off automatically."""

        tools, sessions = await get_tools(sandbox=str(DATA_DIR))
        conn, checkpointer = await get_sqlite_connection()
        model = ChatOpenAI(
            model=MODEL_NAME,
            base_url=URL,
            api_key=API_KEY
        )

        graph = create_agent(
            model=model,
            tools=tools,
            system_prompt=BASE_SYSTEM_PROMPT,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={"edit_file": True, "move_file": True}
                ),
                TodoListMiddleware(),
                ModelCallLimitMiddleware(run_limit=100),
                TolerateToolErrors(),
                LogToolUsage(),
                ImageToolGuardrail(),
                OverwriteGuardrail()
            ],
            checkpointer=checkpointer,
        )
        return cls(conn, checkpointer, graph, thread_id, tools, sessions)


    async def run_turn(self, message: str, success_criteria: str, history: list) -> list:
        """One turn of conversation: the worker attempts the task and the evaluator checks it,
        retrying with feedback up to MAX_ATTEMPTS. If the worker pauses for approval, this
        returns straight away with paused set, and resume() continues the same turn."""
        self.task = message
        self.success_criteria = success_criteria or "The answer should be clear, correct and complete"
        self.attempts = 0
        self.todos = []
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": f"{message}\n\n",
                }
            ]
        }
        return await self._advance(payload, history + [{"role": "user", "content": message}])

    async def resume(self, history: list) -> list:
        """Approve the actions the worker paused on, and continue the turn."""
        payload = Command(resume={"decisions": [{"type": "approve"}] * self.pending_actions})
        return await self._advance(payload, history)

    async def _advance(self, payload, history: list) -> list:
        config = {"configurable": {"thread_id": self.thread_id}}
        while True:
            result = None
            async for result in self._graph.astream(payload, config=config, stream_mode="values"):
                self.todos = result.get("todos", self.todos)

            if "__interrupt__" in result:
                actions = result["__interrupt__"][0].value["action_requests"]
                self.paused = True
                self.pending_actions = len(actions)
                described = "\n".join(action["description"] for action in actions)
                return history + [{"role": "assistant", "content": f"Waiting for your approval:\n{described}"}]

            self.paused = False
            reply = result["messages"][-1].content
            tools_used = [
                call["name"] for m in result["messages"] for call in (getattr(m, "tool_calls", None) or [])
            ]
            self.attempts += 1

            verdict = await self.evaluate(self.task, self.success_criteria, reply, tools_used)
            if verdict.success_criteria_met or verdict.user_input_needed or self.attempts >= MAX_ATTEMPTS:
                return history + [
                    {"role": "assistant", "content": reply}]
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Your last response did not meet the success criteria. "
                                   f"Here is the feedback: {verdict.feedback}. Please keep working and address it.",
                    }
                ]
            }

    async def evaluate(
            self, message: str, success_criteria: str, last_reply: str, tools_used: list[str]
    ) -> EvaluatorOutput:
        prompt = f"""
        You decide whether an assistant has met the success criteria for a task.

        The user's request was:
        {message}

        The success criteria are:
        {success_criteria}

        The tools the assistant called while working, in order:
        {", ".join(tools_used) or "none"}

        The assistant's most recent reply was:
        {last_reply}

        Decide whether the success criteria are met, using the tool calls as evidence of what was actually done.
        Also decide whether the assistant needs more input from the user, either because it asked a question,
        needs clarification, or seems stuck. Give brief, concrete feedback.

        Your answer is a JSON structure, no code, no markdown, following the {EvaluatorOutput.model_json_schema()} structure:
        """ + """
        Example:  
        { 
        "property1": "value1",
        "property2": "value2",
        ...
        }
        
        IMPORTANT: First token of your answer is {
        """
        return await self.evaluator.ainvoke(prompt)

    async def cleanup(self):
        """Shut down SQLite connection and MCP Sessions"""
        await self._conn.close()
        if self._sessions:
            self._sessions.stop()