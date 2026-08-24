from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    TodoListMiddleware)
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
import aiosqlite
import os
from dotenv import load_dotenv

from .wiki_agent_tools import get_tools, McpSessions, EvaluatorOutput
from src import DATA_DIR, MEMORY_DIR

load_dotenv()

class TolerateToolErrors(AgentMiddleware):
    """Hand tool failures back to the model as a message so it can recover, rather than
    crashing the run. Tools that touch the outside world, like a browser, fail now and then."""

    async def awrap_tool_call(self, request, handler):
        try:
            return await handler(request)
        except Exception as error:
            return ToolMessage(
                content=f"That tool call failed: {error}. Try another approach.",
                tool_call_id=request.tool_call["id"],
            )


BASE_SYSTEM_PROMPT = SystemMessage(
    """
    You are an experienced project manager. Your role is to assist a team in managing information about European Projects.
    You are a direct, precise manager who organizes information and create links into an organized structures.
    
    Your working method is precise. You organize project information into a wikipedia-like structure.
    You have also access to important project documentation. Documentation is quite heavyweight, so you read them once and create
    your wiki.
    
    Here's how your data is organized:
    - Sources -> Folder that contain several files (documentation, PDF files). You cannot modify any file in this folder, only read files inside
        Use your PDF reading tools here to read information
    
    - wiki -> Here it is your playground. You can create folders and files, edit files with new information. 
        In your wiki it is really important to create links between files, so that it is easy to browse information and create links
    
    
    To better organize the wiki folder, you should follow this structure, where markdown describes how to nest and what should contain:
    
    # Partners
    > Folder containing all project partners.
    
    ## PartnerX
    > Folder containing all information related to a specific partner.
    
    ### Role.md
    > Summary of the partner's role in the project.
    > Contains links to the relevant Work Packages (WPs), Tasks, and assigned Project Managers (PMs).
    
    ### People
    > Folder containing profiles of people belonging to the partner.
    
    #### PersonX.md
    > Personal profile of a person, including a brief psychological/personality profile and relevant skills or competencies, if available.
    
    
    # WPs
    > Folder containing all Work Packages (WPs) in the project.
    
    ## WP
    > Folder containing all information related to a specific Work Package.
    
    ### Summary.md
    > Summary of the WP, including its role in the project and an overview of its Tasks.
    
    ### Task_X
    > Folder containing all information related to a specific Task.
    
    #### Summary.md
    > Description of the Task, its Task Leader, and the Partners involved.
    > Also records progress and relevant updates concerning the Task.
    
    #### Assets.md
    > Documentation and references for assets developed within the Task for the Partners.
    
    #### Studies.md
    > References to relevant studies, research papers, articles, and other scientific or technical material related to the Task.
    
    #### Synergies.md
    > Documents connections and synergies between this Task and other Tasks.
    > Contains links and a description of how the Tasks are related.
    
    #### TODOs
    > Folder containing ongoing TODO items related to the Task.
    
    ##### [date_start - date_end] TodoX.md
    > File describing an ongoing TODO.
    > The filename specifies the expected start and end dates.
    
    #### Completed
    > Folder containing TODOs that have been completed.
    
    ##### TodoX.md
    > A completed TODO moved from the TODOs folder after completion.
    """
)

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
        self.tools = tools,
        self._sessions = sessions
        self._evaluator = None
        self.task = None
        self.success_criteria = None
        self.todos = []
        self.evalauator = ChatOllama(
            model=os.getenv("MODEL_NAME", "")
        ).with_structured_output(EvaluatorOutput)

    @classmethod
    async def setup(cls, thread_id: str):
        if not os.path.isdir(MEMORY_DIR):
            os.mkdir(MEMORY_DIR)

        conn = await aiosqlite.connect("./memory/memory.db")
        checkpointer = AsyncSqliteSaver(conn)
        model = os.getenv("MODEL")
        tools, sessions = await get_tools(sandbox=DATA_DIR)

        graph = create_agent(
            model=f"ollama:{model}",
            tools=tools,
            system_prompt=BASE_SYSTEM_PROMPT,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={"edit_file": True, "move_file": True}
                ),
                TodoListMiddleware(),
                ModelCallLimitMiddleware(run_limit=30),
                TolerateToolErrors(),
            ],
            checkpointer=checkpointer,
        )
        return cls(conn, checkpointer, graph, thread_id, tools, sessions)

    async def ask(self, message: str, history: list) -> list:
        """
        Sets up the Agent in "Read" mode.
        Then starts a flow to ask questions about the current wiki
        :param message: The user question
        :param history: The past history
        :return:
        """
        success_criteria = "You successfully read the Wiki and answer the user question without leaving doubts"
        return await self._run_turn(message, success_criteria, history)

    async def enrich(self, filepath: str):
        """
        A flow to enrich the current wiki
        :return:
        """
        message = f"""Organize your wiki adding the following file to your information. 
        Use the structure you know to understand where to place new files and update information only if needed.
        Take particular care at person names and organization to understand where to place information.
        
        Answer with the list of modified files and a summary of what you changed.
        Here's the new file: {filepath}
        """

        success_criteria = "Read the file and create / update the wiki accordingly. Success if all information are put in wiki"
        return await self._run_turn(message, success_criteria, [])

    async def _run_turn(self, message: str, success_criteria: str, history: list) -> list:
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
                    "content": f"{message}\n\nThe success criteria for this task are: {self.success_criteria}",
                }
            ]
        }
        return await self._advance(payload, history + [{"role": "user", "content": message}])

    async def resume(self, history: list) -> list:
        """Approve the actions the worker paused on, and continue the turn."""
        payload = Command(resume={"decisions": [{"type": "approve"}] * self.pending_actions})
        return await self._advance(payload, history)

    async def _advance(self, payload, history: list) -> list:
        config = {"configurable": {"thread_id": self.sidekick_id}}
        while True:
            result = None
            async for result in self.worker.astream(payload, config=config, stream_mode="values"):
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
            if  self.attempts >= 3:
                return history + [
                    {"role": "assistant", "content": reply},
                    {"role": "assistant", "content": f"Evaluator: {verdict.feedback}"},
                ]
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

        Your answer is a JSON answer, no code, no markdown, following the {EvaluatorOutput.model_json_schema()} structure:
        """ + """
        Example:  
        { 
        "property1": "value1",
        "property2": "value2",
        ...
        }

        """
        return await self.evaluator.ainvoke(prompt)


    def cleanup(self):
        """Shut down SQLite connection and MCP Sessions"""
        self._conn.close()
        if self._sessions:
            self._sessions.stop()

