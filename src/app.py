"""Gradio app for the Wiki Agent. Run with: uv run app.py

Delete confirmation uses a plain gr.Group toggled by visible=, styled as a
fixed-position overlay in styles.py. Not gr.Modal: that turned out not to
exist in this Gradio install (AttributeError), so don't reintroduce it
without checking `python -c "import gradio; print(gradio.__version__)"`
against what actually ships a Modal component first.
"""

import asyncio
import html
import uuid
import os
from PyPDF2 import PdfReader, PdfWriter

from src import DATA_DIR

import gradio as gr

import src.styles
from src.agents.master.master import WikiAgent
from src.memory.manager import list_threads, load_history, delete_thread

LAUNCH_STYLE = {"theme": styles.THEME, "css": styles.CSS, "head": styles.HEAD}

HEADER = """
<div id="header">
    <div class="context-label">European Projects Office</div>
    <h1>EuroFMX Agent</h1>
</div>
"""

EDIT_BANNER = """
<div class="edit-banner">
    <strong>Edit mode is active.</strong>
    The AI can make mistakes and may create or modify wiki files directly from this chat.
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
    does not detect or restore the pending-approval state.
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


async def send_message(agent, message, history, mode):
    """Wired to the chat textbox/button. Which agent method gets called
    depends on the mode switch: Ask mode is framed as read-only (agent.ask),
    Edit mode allows the same box to create or update wiki files directly,
    e.g. quick notes (agent.enrich). Both still go through the same
    HumanInTheLoopMiddleware for actual file edits/moves either way; the
    difference is the success-criteria framing given to the model, not a
    hard permission wall.
    """
    if agent is None or not message:
        return history, gr.update(visible=False), agent, message
    if mode == "Edit":
        history = await agent.enrich(message, history)
    else:
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

    Locks the ask box and upload control. Locking matters, not just
    cosmetics: ask()/enrich() drive the same LangGraph thread_id, and letting
    a message fire into the graph while an enrich() run is mid-flight on the
    same thread is a race, not a supported concurrent use of the checkpointer.
    """
    if pdf_file is None:
        return history, gr.update(interactive=True), gr.update(interactive=True)

    return history, gr.update(interactive=False), gr.update(interactive=False)


async def enrich_file(agent, pdf_file, history):
    """Runs the actual PDF processing and calls WikiAgent.enrich."""
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

    uploading_message = "\n".join(list_names)

    return await send_message(agent, uploading_message, history, "Edit")



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


def toggle_mode(mode):
    """Ask <-> Edit switch. Restyles the whole shell via a single CSS class
    (see styles.py: .mode-edit overrides the --blue/--gold custom properties
    to red tones, which cascades to everything already built on var(--blue)
    etc., rather than duplicating every color rule for a second mode), shows
    the "AI can make mistakes" badge, and only exposes the upload button in
    Edit mode since enrich() is a file-driven edit operation, out of place
    in a mode framed as read-only.
    """
    is_edit = mode == "Edit"
    return (
        gr.update(elem_classes=["mode-edit"] if is_edit else []),  # app_shell
        gr.update(visible=is_edit),                                 # edit_banner
        gr.update(interactive=is_edit),                                 # pdf_upload
    )


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
            None, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=False), None, gr.update(),
        )

    await delete_thread(thread_id)
    sessions_update = await refresh_sessions()

    if agent is not None and getattr(agent, "thread_id", None) == thread_id:
        agent, chat, approve_upd, ask_upd, pdf_upd, tag = await new_conversation()
    else:
        agent, chat, approve_upd, ask_upd, pdf_upd, tag = (
            agent, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        )

    return (
        agent, chat, approve_upd, ask_upd, pdf_upd, tag,
        gr.update(visible=False), None, sessions_update,
    )


with gr.Blocks(title="Wiki Agent") as ui:
    gr.HTML(HEADER)
    session_tag = gr.HTML(render_session_tag("pending" + "-" * 8))
    agent_state = gr.State(delete_callback=free_resources)
    delete_target = gr.State(None)

    with gr.Group(visible=False, elem_id="delete-modal") as delete_modal:
        with gr.Column(elem_id="delete-modal-card"):
            gr.Markdown("### Delete this conversation?\nThis can't be undone.")
            with gr.Row():
                cancel_delete_btn = gr.Button("Cancel")
                confirm_delete_btn = gr.Button("Delete", variant="stop")
    with gr.Row():

        with gr.Column(scale=1, min_width=220, elem_id="sessions-sidebar"):
            new_conv_button = gr.Button(
                "New conversation", elem_id="new-conv-button", variant="primary"
            )
            mode_switch = gr.Radio(
                ["Ask", "Edit"], value="Ask", label="Mode", elem_id="mode-switch",
            )
            session_list = gr.Radio(
                choices=[], label="Recent sessions", elem_id="session-list",
                interactive=True,
            )
            delete_session_button = gr.Button(
                "🗑 Delete selected session", elem_id="delete-session-button",
                variant="secondary",
            )

        with gr.Column(scale=4, elem_id="app-shell") as app_shell:
            edit_banner = gr.HTML(EDIT_BANNER, visible=False, elem_id="edit-banner")

            with gr.Row():
                with gr.Column(scale=3):
                    gr.HTML('<div class="panel-tab">Consultation</div>')
                    chatbot = gr.Chatbot(
                        label="Wiki Agent", height=420, elem_id="chat",
                        show_label=False,
                    )

                    with gr.Group(elem_id="ask-panel"):
                        with gr.Row():
                            pdf_upload = gr.UploadButton(
                                label="🔗",
                                file_types=[".pdf"],
                                elem_id="upload-button",
                                interactive=False,
                            )
                            message = gr.Textbox(
                                show_label=False, placeholder="Ask about the wiki...", scale=4
                            )
                            ask_button = gr.Button(
                                "💬", scale=1, interactive=False, elem_id="ask-button"
                            )
                with gr.Column(scale=1):
                    gr.HTML('<div class="panel-tab">Case file — plan</div>')
                    todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")

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

    # Ask <-> Edit: restyle the shell, show/hide the warning banner, gate the
    # upload button to Edit mode.
    mode_switch.change(toggle_mode, [mode_switch], [app_shell, edit_banner, pdf_upload])

    # Picking a sidebar entry reattaches a WikiAgent to that thread_id and
    # rebuilds the chat log from its last checkpoint.
    session_list.change(resume_conversation, [session_list], outputs)

    # Delete: pick a session, confirm in the modal, delete + refresh the list.
    # Falls back to a fresh conversation if the deleted thread was the active one.
    delete_session_button.click(
        open_delete_modal, [session_list], [delete_modal, delete_target]
    )
    cancel_delete_btn.click(cancel_delete, None, [delete_modal, delete_target])
    confirm_delete_btn.click(
        confirm_delete, [delete_target, agent_state],
        outputs + [delete_modal, delete_target, session_list],
    )

    # Live plan panel, independent of the long-running ask/enrich calls.
    # Each event listener queues on its own by default in Gradio (concurrency_limit=1
    # PER LISTENER, not shared app-wide), so this tick is not blocked by ask/enrich
    # running.
    timer.tick(watch_todos, [agent_state], [todos_panel], show_progress="hidden")

    # 2) Chat-style interface calling ask() or enrich() depending on mode.
    # Refreshed after: a new thread's first turn is what actually creates its
    # first checkpoint row, so this is the first point the thread can show up
    # in the sidebar at all.
    message.submit(
        send_message, [agent_state, message, chatbot, mode_switch],
        [chatbot, approve_button, agent_state, message],
    ).then(refresh_sessions, None, [session_list])
    ask_button.click(
        send_message, [agent_state, message, chatbot, mode_switch],
        [chatbot, approve_button, agent_state, message],
    ).then(refresh_sessions, None, [session_list])
    approve_button.click(approve, [agent_state, chatbot], [chatbot, approve_button, agent_state])

    # 3) Upload button (Edit mode only) calling "enrich" as soon as a file is
    # submitted. Three stages: announce + lock, do the work, unlock + clear + refresh.
    pdf_upload.upload(
        start_enrich_ui, [pdf_upload, chatbot], [chatbot, pdf_upload, ask_button]
    ).then(
        enrich_file, [agent_state, pdf_upload, chatbot], [chatbot, approve_button, agent_state]
    ).then(
        finish_enrich_ui, None, [pdf_upload, ask_button]
    ).then(refresh_sessions, None, [session_list])


if __name__ == "__main__":
    # Gradio 6: theme/css/head are launch() arguments, not Blocks() arguments.
    ui.launch(inbrowser=True, **LAUNCH_STYLE, server_port=7860)