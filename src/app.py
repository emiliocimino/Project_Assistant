"""Gradio app for the Wiki Agent. Run with: uv run app.py

Written against Gradio 6. The one change Gradio 6 forces on this file: `theme`,
`css`, and `head` are no longer accepted by the gr.Blocks() constructor. They
now live on .launch() instead. Everything else here (Timer, State with
delete_callback, Chatbot in messages format) is unchanged in Gradio 6.
"""

import asyncio
import html
import uuid
import os
from PyPDF2 import PdfReader, PdfWriter

from src import DATA_DIR

import gradio as gr

import styles

# Adjust this import to match where WikiAgent actually lives in your project
from src.wiki_agent import WikiAgent
from src.memory.manager import list_threads, load_history

LAUNCH_STYLE = {"theme": styles.THEME, "css": styles.CSS, "head": styles.HEAD}

HEADER = """
<div id="header">
    <div class="context-label">European Projects Office</div>
    <h1>EuroFMX Agent</h1>
</div>
"""

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
    return f'<h3>Plan</h3><ul>{"".join(rows)}</ul>'


def render_session_tag(thread_id):
    return f'<div class="session-tag">Case file <span class="dot">&middot;</span> REF {thread_id[:8].upper()}</div>'


async def new_conversation():
    """'New conversation': spin up a fresh thread id and a fresh WikiAgent bound to it."""
    thread_id = str(uuid.uuid4())
    agent = await WikiAgent.setup(thread_id)
    return (
        agent,                          # agent_state
        [],                             # chatbot cleared
        gr.update(visible=False),       # approve button hidden
        gr.update(interactive=True),    # ask button enabled
        gr.update(value=None),          # pdf uploader cleared
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
    does not detect or restore the pending-approval state. See the note above
    list_threads/load_history in wiki_agent.py.
    """
    if not thread_id:
        return (
            None, [], gr.update(visible=False), gr.update(interactive=True),
            gr.update(value=None), render_session_tag("none" + "-" * 8),
        )
    agent = await WikiAgent.setup(thread_id)
    history = await load_history(thread_id)
    return (
        agent, history, gr.update(visible=False), gr.update(interactive=True),
        gr.update(value=None), render_session_tag(thread_id),
    )


async def ask(agent, message, history):
    """Wired to the ChatInterface-style textbox; calls WikiAgent.ask."""
    if agent is None or not message:
        return history, gr.update(visible=False), agent, message
    history = await agent.ask(message, history)
    paused = getattr(agent, "paused", False)
    return history, gr.update(visible=paused), agent, ""


async def approve(agent, history):
    """Continues a turn that paused for human-in-the-loop approval."""
    if agent is None:
        return history, gr.update(visible=False), agent
    history = await agent.resume(history)
    paused = getattr(agent, "paused", False)
    return history, gr.update(visible=paused), agent


def start_enrich_ui(pdf_file, history):
    """Runs the instant the file lands, before any PDF processing starts.

    Writes a visible "working on it" turn immediately and locks the ask box
    and upload control. Locking matters, not just cosmetics: ask() and
    enrich() drive the same LangGraph thread_id, and letting a question fire
    into the graph while an enrich() run is mid-flight on the same thread is
    a race, not a supported concurrent use of the checkpointer.
    """
    if pdf_file is None:
        return history, gr.update(interactive=True), gr.update(interactive=True)
    filename = os.path.basename(pdf_file)
    history = history + [
        {"role": "user", "content": f"Uploaded: {filename}"},
        {
            "role": "assistant",
            "content": f"Reading **{filename}** and updating the wiki now. "
                        f"This can take a few minutes for larger files.",
        },
    ]
    return history, gr.update(interactive=False), gr.update(interactive=False)


async def enrich_file(agent, pdf_file, history):
    """Runs the actual PDF processing and calls WikiAgent.enrich.

    NOTE (fixed earlier): list_names.append used to sit inside the
    `if not os.path.isfile` branch, so re-processing a file whose pages were
    already extracted produced an empty list_names and called agent.enrich("").
    The append now runs regardless of whether the page file was just written
    or already existed.
    """
    if agent is None or pdf_file is None:
        return history, gr.update(visible=False), agent

    filename = os.path.basename(pdf_file).split("/")[-1].replace(" ", "_")

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

    turn = await agent.enrich("\n".join(list_names))
    # enrich() rebuilds its own history from scratch (see WikiAgent.enrich),
    # so turn[0] is the raw internal instruction block sent to the model, not
    # something a user should see. Drop it and append the rest.
    if turn and turn[0].get("role") == "user":
        turn = turn[1:]
    history = history + turn
    paused = getattr(agent, "paused", False)
    return history, gr.update(visible=paused), agent


def finish_enrich_ui():
    """Unlocks the controls once enrich_file has returned, and clears the upload
    slot so a repeat drop of the same file re-triggers the .upload() event."""
    return gr.update(value=None, interactive=True), gr.update(interactive=True)


def watch_todos(agent):
    """Timer-driven read of the agent's to do list. Kept as the plan panel's only writer:
    if a long-running ask/enrich call owned the panel as an output, Gradio would mark it
    pending and live progress would not render while the agent works."""
    return render_todos(agent.todos) if agent else render_todos([])


def free_resources(agent):
    """Best-effort async cleanup when the State is dropped (new conversation / tab close).

    Known limitation, not something fixable from here: Gradio's delete_callback for
    gr.State is documented but has open reports of not firing reliably on tab close
    or reload (gradio-app/gradio#8241). Treat this as opportunistic cleanup, not a
    guarantee every session gets its sqlite connection closed.
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


with gr.Blocks(title="Wiki Agent") as ui:
    gr.HTML(HEADER)
    session_tag = gr.HTML(render_session_tag("pending" + "-" * 8))
    agent_state = gr.State(delete_callback=free_resources)

    with gr.Row():
        with gr.Column(scale=1, min_width=220, elem_id="sessions-sidebar"):
            new_conv_button = gr.Button(
                "New conversation", elem_id="new-conv-button", variant="primary"
            )
            session_list = gr.Radio(
                choices=[], label="Recent sessions", elem_id="session-list",
                interactive=True,
            )

        with gr.Column(scale=4):
            with gr.Row():
                chatbot = gr.Chatbot(
                    label="Wiki Agent", height=420, scale=3, elem_id="chat",
                    show_label=False,
                )
                with gr.Column(scale=1):
                    todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")

            with gr.Group(elem_id="ask-panel"):
                with gr.Row():
                    message = gr.Textbox(
                        show_label=False, placeholder="Ask about the wiki...", scale=4
                    )
                    ask_button = gr.Button(
                        "Ask", scale=1, interactive=False, elem_id="ask-button"
                    )

            with gr.Row():
                pdf_upload = gr.File(
                    label="Drop a project document here to enrich the wiki",
                    file_types=[".pdf"],
                    elem_id="pdf-upload"
                )

            approve_button = gr.Button(
                "Approve and continue", visible=False, elem_id="approve-button"
            )

    timer = gr.Timer(1)

    outputs = [agent_state, chatbot, approve_button, ask_button, pdf_upload, session_tag]

    # 1) New conversation -> instantiate a fresh WikiAgent on a fresh thread,
    # then refresh the sidebar so the new thread appears in the list.
    ui.load(new_conversation, [], outputs).then(refresh_sessions, None, [session_list])
    new_conv_button.click(
        new_conversation, [], outputs
    ).then(refresh_sessions, None, [session_list])

    # Picking a sidebar entry reattaches a WikiAgent to that thread_id and
    # rebuilds the chat log from its last checkpoint.
    session_list.change(resume_conversation, [session_list], outputs)

    # Live plan panel, independent of the long-running ask/enrich calls.
    # Each event listener queues on its own by default in Gradio (concurrency_limit=1
    # PER LISTENER, not shared app-wide), so this tick is not blocked by ask/enrich
    # running. If it still doesn't update live, the cause is elsewhere: see the
    # note above render_todos about confirming the "todos" state key.
    timer.tick(watch_todos, [agent_state], [todos_panel], show_progress="hidden")

    # 2) Chat-style interface calling "ask". Refreshed after: a new thread's
    # first turn is what actually creates its first checkpoint row, so this
    # is the first point the thread can show up in the sidebar at all.
    message.submit(
        ask, [agent_state, message, chatbot], [chatbot, approve_button, agent_state, message]
    ).then(refresh_sessions, None, [session_list])
    ask_button.click(
        ask, [agent_state, message, chatbot], [chatbot, approve_button, agent_state, message]
    ).then(refresh_sessions, None, [session_list])
    approve_button.click(approve, [agent_state, chatbot], [chatbot, approve_button, agent_state])

    # 3) PDF uploader calling "enrich" as soon as a file is submitted.
    # Three stages: announce + lock, do the work, unlock + clear + refresh sidebar.
    pdf_upload.upload(
        start_enrich_ui, [pdf_upload, chatbot], [chatbot, pdf_upload, ask_button]
    ).then(
        enrich_file, [agent_state, pdf_upload, chatbot], [chatbot, approve_button, agent_state]
    ).then(
        finish_enrich_ui, None, [pdf_upload, ask_button]
    ).then(refresh_sessions, None, [session_list])


if __name__ == "__main__":
    # Gradio 6: theme/css/head are launch() arguments, not Blocks() arguments.
    ui.launch(inbrowser=True, **LAUNCH_STYLE)