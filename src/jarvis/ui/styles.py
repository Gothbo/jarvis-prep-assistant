"""
JARVIS Design System — Styles Module
CSS tokens, global styles, and reusable HTML components for Streamlit.

Usage:
    from jarvis.ui.styles import inject_css
    inject_css()  # call once at the top of each page
"""

import streamlit as st

from jarvis.ui.icons import icon

# ── CSS Tokens & Global Styles ──────────────────────────────────────────────

_GLOBAL_CSS = """
<style>
:root {
    /* Brand Colors */
    --jarvis-primary: #6366f1;
    --jarvis-primary-light: #818cf8;
    --jarvis-primary-bg: #eef2ff;
    --jarvis-success: #10b981;
    --jarvis-success-bg: #ecfdf5;
    --jarvis-danger: #ef4444;
    --jarvis-danger-bg: #fef2f2;
    --jarvis-warning: #f59e0b;
    --jarvis-warning-bg: #fffbeb;
    --jarvis-text: #1e293b;
    --jarvis-text-secondary: #64748b;
    --jarvis-text-muted: #94a3b8;
    --jarvis-border: #e2e8f0;
    --jarvis-surface: #ffffff;
    --jarvis-background: #f8fafc;

    /* Spacing (8px grid) */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 24px;
    --space-6: 32px;
    --space-8: 48px;

    /* Radius */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;

    /* Typography */
    --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
}

/* ── Sidebar ───────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    width: 300px !important;
    min-width: 300px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {
    white-space: nowrap;
    overflow: visible;
    text-overflow: clip;
}

/* ── Global overrides ──────────────────────────────────────────── */
.stApp {
    background-color: var(--jarvis-background);
}
h1, h2, h3, h4 {
    font-family: var(--font-body);
    color: var(--jarvis-text);
}

/* ── Feature Card ──────────────────────────────────────────────── */
.jarvis-card {
    background: var(--jarvis-surface);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: var(--space-5);
    transition: all 200ms ease;
    cursor: pointer;
    height: 100%;
}
.jarvis-card:hover {
    border-color: var(--jarvis-primary);
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.12);
    transform: translateY(-2px);
}
.jarvis-card .card-icon {
    margin-bottom: var(--space-3);
}
.jarvis-card h4 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 var(--space-2) 0;
    color: var(--jarvis-text);
}
.jarvis-card p {
    font-size: 13px;
    color: var(--jarvis-text-secondary);
    line-height: 1.6;
    margin: 0;
}
.jarvis-card .card-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: var(--space-3);
    font-size: 13px;
    font-weight: 500;
    color: var(--jarvis-primary);
    text-decoration: none;
}
/* ── Text Area ─────────────────────────────────────────────────── */
div[data-testid="stTextArea"] textarea {
    border: 1.5px solid var(--jarvis-border) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--jarvis-surface) !important;
    padding: var(--space-3) var(--space-4) !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    color: var(--jarvis-text) !important;
    transition: border-color 200ms ease, box-shadow 200ms ease;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--jarvis-primary) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}
div[data-testid="stTextArea"] textarea::placeholder {
    color: var(--jarvis-text-muted) !important;
}

/* ── Section Label ─────────────────────────────────────────────── */
.jarvis-section-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--jarvis-text);
    margin: var(--space-5) 0 var(--space-3) 0;
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

/* Card overlay CSS is injected per-page, not globally, because different
 * pages have different horizontal-block layouts. See Home.py and Prep.py. */

/* ── Result Section Card ───────────────────────────────────────── */
.jarvis-section {
    background: var(--jarvis-surface);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: var(--space-5);
    margin-bottom: var(--space-4);
}
.jarvis-section-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-3);
    border-bottom: 1px solid var(--jarvis-border);
}
.jarvis-section-header h3 {
    font-size: 16px;
    font-weight: 600;
    margin: 0;
    color: var(--jarvis-text);
}
.jarvis-section .content {
    font-size: 14px;
    line-height: 1.7;
    color: var(--jarvis-text);
}

/* ── Template Card ─────────────────────────────────────────────── */
.jarvis-template {
    background: var(--jarvis-surface);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: var(--space-4) var(--space-5);
    cursor: pointer;
    transition: all 200ms ease;
    text-align: left;
}
.jarvis-template:hover {
    border-color: var(--jarvis-primary);
    background: var(--jarvis-primary-bg);
}
.jarvis-template.active {
    border-color: var(--jarvis-primary);
    background: var(--jarvis-primary-bg);
    box-shadow: 0 0 0 2px var(--jarvis-primary);
}
.jarvis-template h5 {
    font-size: 14px;
    font-weight: 600;
    margin: 0 0 4px 0;
    color: var(--jarvis-text);
}
.jarvis-template p {
    font-size: 12px;
    color: var(--jarvis-text-muted);
    margin: 0;
}

/* ── Toolbar ───────────────────────────────────────────────────── */
.jarvis-toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) 0;
}
.jarvis-toolbar-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-sm);
    background: var(--jarvis-surface);
    color: var(--jarvis-text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 150ms ease;
    text-decoration: none;
}
.jarvis-toolbar-btn:hover {
    border-color: var(--jarvis-primary);
    color: var(--jarvis-primary);
    background: var(--jarvis-primary-bg);
}

/* ── Status Badge ──────────────────────────────────────────────── */
.jarvis-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 500;
}
.jarvis-badge--success {
    background: var(--jarvis-success-bg);
    color: #065f46;
}
.jarvis-badge--danger {
    background: var(--jarvis-danger-bg);
    color: #991b1b;
}
.jarvis-badge--warning {
    background: var(--jarvis-warning-bg);
    color: #92400e;
}
.jarvis-badge--info {
    background: var(--jarvis-primary-bg);
    color: #3730a3;
}

/* ── Step Indicator ────────────────────────────────────────────── */
.jarvis-step {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-sm);
    font-size: 14px;
}
.jarvis-step--done {
    color: var(--jarvis-success);
}
.jarvis-step--active {
    color: var(--jarvis-primary);
    background: var(--jarvis-primary-bg);
}
.jarvis-step--pending {
    color: var(--jarvis-text-muted);
}
.jarvis-step--warning {
    color: var(--jarvis-warning);
    background: var(--jarvis-warning-bg);
}

/* ── Hide Streamlit defaults ───────────────────────────────────── */
#MainMenu, header {visibility: hidden;}
footer {visibility: hidden;}

/* ── Core Prep Labels ──────────────────────────────────────────── */
.core-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--jarvis-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

/* ── Solution Outline Items ────────────────────────────────────── */
.outline-item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 12px;
    padding: 10px 14px;
    background: var(--jarvis-background);
    border-radius: var(--radius-sm);
    border-left: 3px solid var(--jarvis-primary);
}
.outline-num {
    font-size: 13px;
    font-weight: 700;
    font-style: normal;
    color: var(--jarvis-primary);
    min-width: 20px;
    padding-top: 1px;
}
.outline-text {
    font-size: 14px;
    font-style: normal;
    font-weight: normal;
    line-height: 1.6;
    color: var(--jarvis-text);
}
</style>
"""


def inject_css():
    """Inject global CSS tokens into the Streamlit page. Call once per page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# ── Reusable HTML Components ────────────────────────────────────────────────


def card(title: str, description: str, icon_name: str, link_text: str = "进入 →") -> str:
    """Render a feature entry card (visual only).

    Interactivity is handled by a transparent st.button() overlay placed
    in the same column. See the "Clickable Card Overlay" CSS in _GLOBAL_CSS.

    Args:
        title: Card heading
        description: Short description (1-2 lines)
        icon_name: Phosphor icon name (from icons.py)
        link_text: CTA text at bottom
    """
    svg = icon(icon_name, size=32, color="var(--jarvis-primary)")
    return f"""
<div class="jarvis-card" style="position:relative;">
    <div class="card-icon">{svg}</div>
    <h4>{title}</h4>
    <p>{description}</p>
    <span class="card-link">{link_text}</span>
</div>
"""


def section_header(title: str, icon_name: str, badge_text: str = "", badge_type: str = "info") -> str:
    """Render a section header with icon and optional badge.

    Args:
        title: Section title
        icon_name: Phosphor icon name
        badge_text: Optional badge text
        badge_type: "info" | "success" | "warning" | "danger"
    """
    svg = icon(icon_name, size=20, color="var(--jarvis-primary)")
    badge_html = ""
    if badge_text:
        badge_html = f'<span class="jarvis-badge jarvis-badge--{badge_type}">{badge_text}</span>'
    return f"""
<div class="jarvis-section-header">
    {svg}
    <h3>{title}</h3>
    {badge_html}
</div>
"""


def result_section(title: str, icon_name: str, content_html: str, badge_text: str = "", badge_type: str = "info") -> str:
    """Render a result section card with header and content.

    Args:
        title: Section title
        icon_name: Phosphor icon name
        content_html: HTML content inside the section
        badge_text: Optional badge (e.g., "3 条")
        badge_type: Badge color type
    """
    header = section_header(title, icon_name, badge_text, badge_type)
    return f"""
<div class="jarvis-section">
    {header}
    <div class="content">{content_html}</div>
</div>
"""


def toolbar_button(label: str, icon_name: str, key: str = "") -> str:
    """Render a toolbar button (for export actions).

    Note: This is visual only — pair with a Streamlit button for actual interaction.
    """
    svg = icon(icon_name, size=16, color="var(--jarvis-text-secondary)")
    return f"""
<div class="jarvis-toolbar">
    <span class="jarvis-toolbar-btn">{svg} {label}</span>
</div>
"""


def badge(text: str, badge_type: str = "info") -> str:
    """Render a status badge.

    Args:
        text: Badge text
        badge_type: "info" | "success" | "warning" | "danger"
    """
    return f'<span class="jarvis-badge jarvis-badge--{badge_type}">{text}</span>'


def step_item(label: str, status: str = "pending", detail: str = "") -> str:
    """Render a step indicator row.

    Args:
        label: Step name
        status: "done" | "active" | "pending" | "warning"
        detail: Optional detail text
    """
    icons_map = {
        "done": icon("check_circle", size=18, color="var(--jarvis-success)"),
        "active": icon("lightning", size=18, color="var(--jarvis-primary)"),
        "pending": icon("info", size=18, color="var(--jarvis-text-muted)"),
        "warning": icon("warning_diamond", size=18, color="var(--jarvis-warning)"),
    }
    step_icon = icons_map.get(status, icons_map["pending"])
    detail_html = f'<span style="margin-left:auto;font-size:12px;color:var(--jarvis-text-muted);">{detail}</span>' if detail else ""
    return f"""
<div class="jarvis-step jarvis-step--{status}">
    {step_icon}
    <span>{label}</span>
    {detail_html}
</div>
"""
