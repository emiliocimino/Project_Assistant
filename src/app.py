"""Gradio app for the Wiki Agent. Run with: uv run app.py"""

import os

import gradio as gr

from src import DATA_DIR
from src.handlers import (
    approve,
    cancel_delete,
    confirm_delete,
    enrich_file,
    finish_enrich_ui,
    free_resources,
    new_conversation,
    open_delete_modal,
    pre_send_message,
    refresh_sessions,
    render_session_tag,
    render_todos,
    resume_conversation,
    send_message,
    start_enrich_ui,
    watch_todos,
)
from src.styles import CSS, HEAD, THEME

LAUNCH_STYLE = {"theme": THEME, "css": CSS, "head": HEAD}
project_title = os.getenv("PROJECT_TITLE", "Project")


HEADER = f"""
<div id="header">
    <div class="context-label">European Projects Office</div>
    <h1>{project_title} Agent</h1>
</div>
"""

EDIT_BANNER = """
<div class="edit-banner">
    <strong>Warning:</strong>
    AI Agents can make mistakes. Any new piece of information may modify the project knowledge base.
</div>
"""


with gr.Blocks(title="Wiki Agent") as ui:
    gr.HTML(HEADER)
    session_tag = gr.HTML(
        render_session_tag("pending" + "-" * 8), visible=False
    )  # TODO: Remove
    agent_state = gr.State(delete_callback=free_resources)
    pending_message = gr.State("")
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
            session_list = gr.Radio(
                choices=[],
                label="Recent sessions",
                elem_id="session-list",
                interactive=True,
            )
            delete_session_button = gr.Button(
                "🗑 Delete selected session",
                elem_id="delete-session-button",
                variant="secondary",
            )

        with gr.Column(
            scale=4, elem_id="app-shell", elem_classes=["mode_edit"]
        ) as app_shell:
            edit_banner = gr.HTML(EDIT_BANNER, visible=True, elem_id="edit-banner")

            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label="Wiki Agent",
                        height="60vh",
                        elem_id="chat",
                        show_label=False,
                    )

                    with gr.Group(elem_id="ask-panel"):
                        with gr.Row():
                            pdf_upload = gr.UploadButton(
                                label="🔗",
                                file_types=[".pdf"],
                                elem_id="upload-button",
                                interactive=True,
                            )
                            text = gr.Textbox(
                                show_label=False,
                                placeholder="Ask about the wiki...",
                                scale=4,
                                max_lines=2,
                            )
                            ask_button = gr.Button(
                                "💬", scale=1, interactive=False, elem_id="ask-button"
                            )
                        with gr.Row():
                            approve_button = gr.Button(
                                "Approve", visible=False, elem_id="approve-button"
                            )
                            reject_button = gr.Button(
                                "Reject", visible=False, elem_id="approve-button"
                            )
                with gr.Column(scale=1):
                    gr.HTML('<div class="panel-tab">Case file — plan</div>')
                    todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")

    timer = gr.Timer(0.1)

    outputs = [
        agent_state,
        chatbot,
        approve_button,
        reject_button,
        ask_button,
        pdf_upload,
        session_tag,
    ]

    # 1) New conversation -> instantiate a fresh WikiAgent on a fresh thread,
    # then refresh the sidebar so the new thread appears in the list.
    ui.load(new_conversation, [], outputs).then(refresh_sessions, None, [session_list])
    new_conv_button.click(new_conversation, [], outputs).then(
        refresh_sessions, None, [session_list]
    )

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
        confirm_delete,
        [delete_target, agent_state],
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
    text.submit(
        pre_send_message, [text, chatbot], [text, chatbot, pending_message]
    ).then(
        send_message,
        [agent_state, pending_message, chatbot],
        [chatbot, approve_button, reject_button, agent_state, pending_message],
    ).then(refresh_sessions, None, [session_list])

    ask_button.click(
        pre_send_message, [text, chatbot], [text, chatbot, pending_message]
    ).then(
        send_message,
        [agent_state, pending_message, chatbot],
        [chatbot, approve_button, reject_button, agent_state, pending_message],
    ).then(refresh_sessions, None, [session_list])

    approve_button.click(
        approve,
        [agent_state, chatbot, approve_button],
        [chatbot, approve_button, reject_button, agent_state],
    )
    reject_button.click(
        approve,
        [agent_state, chatbot, reject_button],
        [chatbot, approve_button, reject_button, agent_state],
    )

    # 3) Upload button (Edit mode only) calling "enrich" as soon as a file is
    # submitted. Three stages: announce + lock, do the work, unlock + clear + refresh.
    pdf_upload.upload(
        start_enrich_ui,
        [pdf_upload, chatbot],
        [chatbot, pdf_upload, ask_button, pending_message],
    ).then(
        enrich_file,
        [agent_state, pdf_upload, chatbot, pending_message],
        [chatbot, approve_button, reject_button, agent_state, pending_message],
    ).then(finish_enrich_ui, None, [pdf_upload, ask_button]).then(
        refresh_sessions, None, [session_list]
    )


if __name__ == "__main__":
    from loguru import logger

    if not os.path.isdir(DATA_DIR):
        os.mkdir(DATA_DIR)
    if not os.path.isdir(DATA_DIR / "wiki"):
        os.mkdir(DATA_DIR / "wiki")
        os.mkdir(DATA_DIR / "sources")

    logger.info("Starting application...")
    ui.launch(**LAUNCH_STYLE)
