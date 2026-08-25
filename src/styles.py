import gradio as gr

# Injected into <head>: preconnect + the three type families used below.
# Renamed from JS -> HEAD: this is HTML link tags for the document head, not
# JavaScript. The old name would have misled the next person wiring this into
# Gradio's head= parameter.
HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link
  href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
  rel="stylesheet">
"""

THEME = gr.themes.Base(
    font=[gr.themes.GoogleFont("IBM Plex Sans"), "sans-serif"],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "monospace"],
).set(
    body_background_fill="#EEF1EF",
    body_text_color="#1C2B39",
    block_background_fill="#FFFFFF",
    block_border_color="#CBD2CE",
    block_border_width="1px",
    block_radius="2px",
    block_shadow="none",
    block_label_text_color="#5B6B66",
    input_background_fill="#FFFFFF",
    input_border_color="#CBD2CE",
    input_border_color_focus="#1F4E8C",
    input_radius="2px",
    button_primary_background_fill="#1F4E8C",
    button_primary_background_fill_hover="#173C6D",
    button_primary_text_color="#F6F7F5",
    button_primary_border_color="#B8892B",
    button_secondary_background_fill="#FFFFFF",
    button_secondary_background_fill_hover="#EEF1EF",
    button_secondary_border_color="#CBD2CE",
    button_secondary_text_color="#1C2B39",
    button_large_radius="2px",
    button_small_radius="2px",
)

CSS = """
:root {
    --paper: #EEF1EF;
    --card: #FFFFFF;
    --ink: #1C2B39;
    --ink-soft: #5B6B66;
    --line: #CBD2CE;
    --blue: #1F4E8C;
    --blue-deep: #173C6D;
    --gold: #B8892B;
    --green: #4B7A5A;
    --amber: #B8892B;
}

.gradio-container {
    background: var(--paper) !important;
    color: var(--ink) !important;
    font-family: "IBM Plex Sans", sans-serif !important;
}

/* ---------- Header: dossier cover ---------- */
#header {
    text-align: left;
    padding: 1.25rem 0 1rem 0;
    border-bottom: 3px double var(--ink);
    margin-bottom: 0.5rem;
}
#header .context-label {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.15rem;
}
#header h1 {
    font-family: "Source Serif 4", serif;
    font-weight: 700;
    font-size: 2.1rem;
    margin: 0;
    color: var(--ink);
}
#header .brand-bar {
    display: none;
}
.session-tag {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    color: var(--ink-soft);
    letter-spacing: 0.04em;
    margin: 0.35rem 0 0.75rem 0;
}
.session-tag .dot {
    color: var(--blue);
}

/* ---------- Delete confirmation (Group + CSS overlay, not gr.Modal) ----------
gr.Modal isn't available in every Gradio install; verify before depending on
a component like that again rather than trusting docs-nav wording. This is
the version-independent fallback: a normal Group, shown/hidden via
visible=, positioned fixed with a backdrop so it reads as a modal. */
#delete-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(28, 43, 57, 0.45);
    z-index: 1000;
}
#delete-modal-card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 1.25rem 1.5rem;
    max-width: 380px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}

/* ---------- Sessions sidebar ---------- */
#sessions-sidebar {
    border-right: 1px solid var(--line);
    padding-right: 0.9rem;
}
#session-list label {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-soft);
}
#session-list .wrap {
    gap: 0.3rem;
    max-height: 320px;
    overflow-y: auto !important;
}
#delete-session-button {
    margin-top: 0.5rem;
    font-size: 0.82rem;
}

/* ---------- Mode switch ---------- */
#mode-switch {
    margin: 0.6rem 0 1rem 0;
}
#mode-switch label {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-soft);
}

/* ---------- Edit mode reskin ----------
Re-declares the same custom properties every other rule in this file already
reads via var(--blue), var(--gold), etc. Scoping the redeclaration under
#app-shell.mode-edit means the override cascades to every descendant that
already uses those variables, no need to duplicate each color rule for a
second mode. */
#app-shell.mode-edit {
    --blue: #8C2A2A;
    --blue-deep: #6E1F1F;
    --gold: #B85C2B;
    --amber: #B85C2B;
}
#app-shell.mode-edit #chat,
#app-shell.mode-edit #plan-panel,
#app-shell.mode-edit #pdf-upload,
#app-shell.mode-edit #ask-panel textarea,
#app-shell.mode-edit #ask-panel input {
    border-color: #D9B3A8 !important;
}

.edit-banner {
    background: #FBEAE6;
    border: 1px solid #D9A08F;
    border-left: 4px solid var(--blue, #8C2A2A);
    color: #5C2A1E;
    font-size: 0.85rem;
    padding: 0.65rem 0.9rem;
    border-radius: 2px;
    margin-bottom: 0.75rem;
}
.edit-banner strong {
    display: block;
    margin-bottom: 0.15rem;
    font-family: "IBM Plex Sans", sans-serif;
}

/* ---------- Panel labels ----------
Plain sibling elements in normal document flow, not an absolutely-positioned
::before sitting on a component's border. The previous approach fought
Gradio's own internal wrapper divs (background/overflow/stacking are not a
stable public contract), which is exactly why the label ended up rendered
behind the chatbot and unreadable. This can't have that problem: it isn't
layered on top of anything. */
.panel-tab {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-soft);
    margin: 0.4rem 0 0.35rem 0.1rem;
}

/* ---------- Folder-tab panels ---------- */
#chat, #plan-panel, #pdf-upload {
    position: relative;
    border: 1px solid var(--line) !important;
    border-radius: 2px !important;
    background: var(--card) !important;
}
#chat { margin-top: 0.1rem; }

/* ---------- Plan / ledger panel ---------- */
#plan-panel {
    margin-top: 0.1rem;
    padding: 1.1rem 1.1rem 1rem 1.1rem;
    max-height: 420px;
    overflow-y: auto !important;
}
#plan-panel h3 {
    font-family: "Source Serif 4", serif;
    font-size: 1rem;
    font-weight: 600;
    margin: 0.1rem 0 0.8rem 0;
    color: var(--ink);
}
#plan-panel .placeholder {
    color: var(--ink-soft);
    font-style: italic;
    font-size: 0.9rem;
}
#plan-panel ul { list-style: none; padding: 0; margin: 0; }

.ledger-row {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--line);
}
.ledger-row:last-child { border-bottom: none; }
.ledger-row .code {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    color: var(--ink-soft);
    flex-shrink: 0;
    padding-top: 0.2rem;
}
.ledger-row .content {
    flex: 1;
    font-size: 0.9rem;
    line-height: 1.35;
    color: var(--ink);
}
.ledger-row.completed .content {
    color: var(--ink-soft);
    text-decoration: line-through;
    text-decoration-color: var(--line);
}

.stamp {
    display: inline-block;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.62rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.12rem 0.4rem;
    border: 1.5px solid currentColor;
    border-radius: 2px;
    transform: rotate(-2deg);
    margin-top: 0.15rem;
    flex-shrink: 0;
}
.stamp.pending { color: var(--blue); }
.stamp.in_progress { color: var(--amber); }
.stamp.completed { color: var(--green); }

/* ---------- Ask panel: form-style, not boxy ---------- */
#ask-panel {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin-top: 0.85rem;
}
#ask-panel textarea, #ask-panel input {
    background: var(--card) !important;
    border: none !important;
    border-bottom: 2px solid var(--line) !important;
    border-radius: 0 !important;
    font-size: 0.95rem !important;
}
#ask-panel textarea:focus, #ask-panel input:focus {
    border-bottom-color: var(--blue) !important;
    box-shadow: none !important;
}

/* ---------- Upload tray ---------- */
#pdf-upload {
    margin-top: 0.1rem;
    border: 1.5px dashed var(--gold) !important;
    background: #FDFAF3 !important;
}

/* ---------- Buttons ---------- */
#new-conv-button, #approve-button, #ask-button {
    font-family: "IBM Plex Sans", sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
}
#approve-button {
    background: var(--gold) !important;
    border-color: var(--gold) !important;
    color: #2A1E05 !important;
}
#approve-button:hover { background: #A47A26 !important; }

/* ---------- Focus visibility ---------- */
button:focus-visible, textarea:focus-visible, input:focus-visible {
    outline: 2px solid var(--gold) !important;
    outline-offset: 2px;
}

/* ---------- Motion (respect reduced-motion) ---------- */
@media (prefers-reduced-motion: no-preference) {
    .stamp { transition: transform 0.15s ease; }
    .ledger-row:hover .stamp { transform: rotate(0deg); }
}

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
    #header h1 { font-size: 1.6rem; }
    #plan-panel { min-height: 220px; }
}
"""