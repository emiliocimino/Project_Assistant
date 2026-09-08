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
#delete-session-button {
    margin-top: 0.5rem;
    font-size: 0.82rem;
}

/* ---------- Session list, reskinned from radio buttons to a chat-style list ----------
gr.Radio is kept for its actual behavior (exactly one selected, stays
selected on click, fires .change()), which is what "textboxes with anchor
that stay selected when clicked" needs functionally. Only the appearance
changes: the native radio circle is hidden and each option's <label> is
styled as a full-width clickable row instead.

Scoping note, same caution as the earlier gr.Modal mistake: `label` is a
real HTML tag, and `input[type="radio"]` is real HTML too, not a guessed
Gradio-internal class name. `label:has(input[type="radio"])` targets only
rows that actually wrap a radio input, which per-option rows do and the
component's own group title (rendered separately) doesn't, so this can't
accidentally restyle the "Recent sessions" title. `:has()` needs a
reasonably current browser (Chrome/Firefox/Safari 2023+); if this doesn't
visually apply, that's the first thing to check, not the class names.
*/
#session-list .wrap {
    max-height: 40vh;
}
#session-list input[type="radio"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}
#session-list label:has(input[type="radio"]) {
    display: block;
    width: 100%;
    padding: 0.55rem 0.75rem;
    margin: 0 0 0.25rem 0;
    border-radius: 4px;
    border: 1px solid transparent;
    cursor: pointer;
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 0.85rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: normal;
    color: var(--ink);
    transition: background 0.12s ease;
}
#session-list label:has(input[type="radio"]):hover {
    background: var(--paper);
}
#session-list label:has(input[type="radio"]:checked) {
    background: #E3E9F5;
    border-color: var(--blue);
    font-weight: 600;
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
#app-shell.mode-edit #ask-panel textarea,
#app-shell.mode-edit #ask-panel input {
    border-color: #D9B3A8 !important;
}

/* ---------- Edit-mode badge ----------
Deliberately NOT in normal document flow. It used to be a full-width HTML
block sitting above the chat, which pushed the chatbot down every time Edit
mode turned on. position: fixed removes it from layout entirely, so turning
it on/off can never shift anything else on the page. It floats in the
top-right corner instead, readable but not disruptive.

Caveat, stated rather than assumed away: position: fixed is relative to the
viewport UNLESS an ancestor element has a `transform` (or a few other
properties) set, in which case it becomes relative to that ancestor instead.
Gradio containers don't set `transform` by default, so this should float
correctly in the corner; if it instead appears to scroll with the page or
lands somewhere unexpected, that ancestor-transform case is what's happening,
and the fix is `position: sticky; top: 0.75rem;` on #edit-banner instead.
*/
#edit-banner {
    position: fixed;
    top: 0.85rem;
    right: 1.1rem;
    z-index: 500;
    max-width: 320px;
}
.edit-banner {
    background: #FBEAE6;
    border: 1px solid #D9A08F;
    border-left: 4px solid var(--blue, #8C2A2A);
    color: #5C2A1E;
    font-size: 0.8rem;
    line-height: 1.35;
    padding: 0.55rem 0.8rem;
    border-radius: 3px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}
.edit-banner strong {
    display: block;
    margin-bottom: 0.1rem;
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
#chat, #plan-panel {
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

/* ---------- Ask panel: one flat pill instead of three separate cards ----------
The previous version resized the buttons themselves but never touched the
box Gradio wraps around each component (UploadButton/Textbox/Button each get
their own white block, border, padding by default from the theme). With
#ask-panel's own background transparent, the page's grey showed through in
the gaps between those three separate white boxes, that was the "ugly grey
space", three cards with gaps, not one bar.

Fix: give #ask-panel itself the pill (white background, border, radius), and
reset every descendant inside it to transparent/borderless so they all read
as content sitting on that one shared surface instead of separate blocks.
Using a wildcard here rather than guessing a specific Gradio block class
name (same reasoning as the label:has() approach above): we want everything
inside this pill flattened regardless of Gradio's internal wrapper structure. */
#ask-panel {
    background: var(--card) !important;
    border: 1px solid var(--line) !important;
    border-radius: 20px !important;
    padding: 0.3rem 0.5rem !important;
    box-shadow: none !important;
    margin-top: 0 !important;
}
#ask-panel > div {
    display: flex !important;
    width: 100% !important;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
}
/* Belt and suspenders: justify-content: space-between above pushes the two
   buttons to the edges on its own, regardless of exact nesting. This
   flex-grow rule is the more precise mechanism, textarea's wrapper
   consumes all remaining space, buttons stay fixed, but it only works if
   #ask-panel > div is actually the row's flex container. If it isn't (one
   more level of Gradio wrapper than expected), space-between still gets you
   "buttons at the edges" even though this rule does nothing. */
#ask-panel > div > *:not(#upload-button):not(#ask-button) {
    flex: 1 1 auto !important;
}
#ask-panel > div > #upload-button,
#ask-panel > div > #ask-button {
    flex: 0 0 auto !important;
}
#ask-panel * {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
#ask-panel textarea, #ask-panel input[type="text"] {
    border-bottom: 2px solid var(--line) !important;
    border-radius: 0 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 0.3rem !important;
    width: 100% !important;
}
#ask-panel textarea:focus, #ask-panel input[type="text"]:focus {
    border-bottom-color: var(--blue) !important;
}
#ask-button, #ask-button button,
#upload-button, #upload-button button {
    min-width: 34px !important;
    width: 34px !important;
    height: 34px !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 50% !important;
    font-size: 1rem !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    align-self: center !important;
    flex-shrink: 0;
}
#ask-button:hover, #ask-button button:hover,
#upload-button:hover, #upload-button button:hover {
    background: var(--paper) !important;
}

/* ---------- Buttons ---------- */
#new-conv-button, #approve-button {
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
    #edit-banner { max-width: calc(100vw - 2rem); }
}
"""