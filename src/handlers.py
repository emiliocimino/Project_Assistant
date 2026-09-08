import asyncio
import html
import os
import uuid

import gradio as gr
from PyPDF2 import PdfReader, PdfWriter

from agents.master.master import WikiAgent
from memory.manager import list_threads, load_history, delete_thread
from src import DATA_DIR

STATUS_LABEL = {"pending": "Open", "in_progress": "In progress", "completed": "Done"}


def render_todos(todos):
    if not todos:
        return '<h3>Plan</h3><div class="placeholder">The agent will file its plan here as it works</div>'
    rows = []
    for i, todo in enumerate(todos, start=1):
        status = todo["status"]
        rows.append(
            f'<li class="ledger-row {status}">'
            f'<span class="code">T-{i:02d}</span>'
            f'<span class="content">{html.escape(todo["content"])}</span>'
            f'<span class="stamp {status}">{STATUS_LABEL.get(status, status)}</span>'
            f"</li>"
        )
    return f"<h3>Plan</h3><ul>{''.join(rows)}</ul>"


def render_session_tag(thread_id):
    return f'<div class="session-tag">Case file <span class="dot">&middot;</span> REF {thread_id[:8].upper()}</div>'


async def new_conversation():
    """'New conversation': spin up a fresh thread id and a fresh WikiAgent bound to it."""
    thread_id = str(uuid.uuid4())
    agent = await WikiAgent.setup(thread_id)
    return (
        agent,  # agent_state
        [],  # chatbot cleared
        gr.update(visible=False),  # approve button hidden
        gr.update(visible=False),  # reject button hidden
        gr.update(interactive=True),  # ask button enabled
        gr.update(value=None),  # pdf uploader cleared
        render_session_tag(thread_id),  # session tag
    )


async def refresh_sessions():
    """Repopulate the sidebar list from the checkpoints table.

    Deliberately omits `value=` from the update. A thread only gets a
    checkpoint row once something has actually been asked or enriched on it,
    so calling this right after new_conversation() won't yet show the thread
    just created, that's expected. Setting value=None here to "deselect"
    would also be wrong for a different reason: Gradio fires .change() on
    programmatic value updates, not just clicks, so that would immediately
    re-trigger session_list.change -> resume_conversation(None) and wipe out
    whatever agent/history the caller just set up. Leaving value untouched
    avoids both problems.
    """
    threads = await list_threads()
    choices = [(t["label"], t["thread_id"]) for t in threads]
    return gr.update(choices=choices)


async def resume_conversation(thread_id):
    """Fires when a sidebar entry is picked. Binds a WikiAgent to the existing
    thread_id (its checkpoint history carries over automatically) and rebuilds
    the visible chat log from that thread's last checkpoint.

    Known gap: if that thread was left mid human-in-the-loop approval, this
    does not detect or restore the pending-approval state.
    """
    if not thread_id:
        return (
            None,
            [],
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(interactive=True),
            gr.update(value=None),
            render_session_tag("none" + "-" * 8),
        )
    agent = await WikiAgent.setup(thread_id)
    history = await load_history(thread_id)
    return (
        agent,
        history,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(interactive=True),
        gr.update(value=None),
        render_session_tag(thread_id),
    )


def pre_send_message(message, history):
    new_history = history + [
        {"role": "user", "content": message},
    ]
    return "", new_history, message


async def send_message(agent, message, history):
    """Wired to the chat textbox/button. Which agent method gets called
    depends on the mode switch: Ask mode is framed as read-only (agent.ask),
    Edit mode allows the same box to create or update wiki files directly,
    e.g. quick notes (agent.enrich). Both still go through the same
    HumanInTheLoopMiddleware for actual file edits/moves either way; the
    difference is the success-criteria framing given to the model, not a
    hard permission wall.

    History is not passed entirely due to message mismatch
    """
    if agent is None or not message:
        return (
            history,
            gr.update(visible=False),
            gr.update(visible=False),
            agent,
            message,
        )

    history = await agent.run_turn(message, history)
    paused = getattr(agent, "paused", False)

    return history, gr.update(visible=paused), gr.update(visible=paused), agent, ""


def start_enrich_ui(pdf_file, history):
    """Runs the instant the file lands, before any PDF processing starts.

    Locks the ask box and upload control. Locking matters, not just
    cosmetics: ask()/enrich() drive the same LangGraph thread_id, and letting
    a message fire into the graph while an enrich() run is mid-flight on the
    same thread is a race, not a supported concurrent use of the checkpointer.
    """

    if pdf_file is None:
        return (
            history,
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )

    filename = os.path.basename(pdf_file).split("/")[-1].replace(" ", "_")
    gr.Info(f"Uploading {filename}...")

    list_names = []
    with open(pdf_file, "rb") as f:
        reader = PdfReader(f)
        for i in range(len(reader.pages)):
            composite_name = DATA_DIR / "sources" / f"page_{i}_{filename}"
            if not os.path.isfile(composite_name):
                output = PdfWriter()
                output.add_page(reader.pages[i])
                with open(composite_name, "wb") as outputStream:
                    output.write(outputStream)
            list_names.append(str(composite_name))

    uploading_message = (
        f"{filename} Uploaded\nUpdate the wiki, making sure to avoid complete overwriting.\nHere the list of file"
        + "\n".join(list_names)
    )

    filename = os.path.basename(pdf_file)

    history = history + [
        {"role": "user", "content": uploading_message},
        {
            "role": "assistant",
            "content": f"Reading **{filename}** and updating the wiki now. "
            f"This can take a few minutes for larger files...",
        },
    ]

    return (
        history,
        gr.update(interactive=False),
        gr.update(interactive=False),
        uploading_message,
    )


async def enrich_file(agent, pdf_file, history, uploading_message):
    """Runs the actual PDF processing and calls WikiAgent.enrich."""
    if agent is None or pdf_file is None:
        return (
            history,
            gr.update(visible=False),
            gr.update(visible=False),
            agent,
            uploading_message,
        )

    return await send_message(agent, uploading_message, history, "Edit")


def finish_enrich_ui():
    """Unlocks the controls once enrich_file has returned, and clears the upload
    slot so a repeat drop of the same file re-triggers the .upload() event."""
    return gr.update(value=None, interactive=True), gr.update(interactive=True)


async def approve(agent, history, action: str):
    """Continues a turn that paused for human-in-the-loop approval."""
    if agent is None:
        return history, gr.update(visible=False), gr.update(visible=False), agent
    action = action.lower()
    decisions = [{"type": action, "message": "Rejected: Do not modify file"}]
    if action == "approve":
        decisions = [{"type": action.lower()}]
    history = await agent.resume(history, decisions)
    paused = getattr(agent, "paused", False)
    return history, gr.update(visible=paused), gr.update(visible=paused), agent


def watch_todos(agent):
    """Timer-driven read of the agent's to do list. Kept as the plan panel's only writer:
    if a long-running ask/enrich call owned the panel as an output, Gradio would mark it
    pending and live progress would not render while the agent works."""
    return render_todos(agent.todos) if agent else render_todos([])


def free_resources(agent):
    """Best-effort async cleanup when the State is dropped (new conversation / tab close).

    Known limitation: Gradio's delete_callback for gr.State has open reports
    of not firing reliably on tab close or reload (gradio-app/gradio#8241).
    Treat this as opportunistic cleanup, not a guarantee.
    """
    if not agent:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(agent.cleanup())
        else:
            loop.run_until_complete(agent.cleanup())
    except RuntimeError:
        pass


def open_delete_modal(thread_id):
    if not thread_id:
        gr.Warning("Pick a session in the list first.")
        return gr.update(visible=False), None
    return gr.update(visible=True), thread_id


def cancel_delete():
    return gr.update(visible=False), None


async def confirm_delete(thread_id, agent):
    """Deletes the picked thread. If it was the currently active session, this
    falls back to starting a fresh conversation rather than leaving the chat
    pointed at a thread_id whose checkpoints no longer exist.
    """
    if not thread_id:
        return (
            None,
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(visible=False),
            None,
            gr.update(),
        )

    await delete_thread(thread_id)
    sessions_update = await refresh_sessions()

    if agent is not None and getattr(agent, "thread_id", None) == thread_id:
        (
            agent,
            chat,
            approve_upd,
            reject_upd,
            ask_upd,
            pdf_upd,
            tag,
        ) = await new_conversation()
    else:
        agent, chat, approve_upd, reject_upd, ask_upd, pdf_upd, tag = (
            agent,
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    return (
        agent,
        chat,
        approve_upd,
        reject_upd,
        ask_upd,
        pdf_upd,
        tag,
        gr.update(visible=False),
        None,
        sessions_update,
    )
