"""
JARVIS Design System — Icon Module
Phosphor-style duotone SVG icons for Streamlit embedding.

Usage:
    from jarvis.ui.icons import icon
    st.markdown(icon("shield_check", size=32, color="#6366f1"), unsafe_allow_html=True)
"""

_ICONS = {
    "shield_check": {
        "primary": '<path d="M128,24L32,56V112c0,56.16,38.4,108.8,96,120,57.6-11.2,96-63.84,96-120V56Z" opacity="0.2"/>',
        "secondary": '<path d="M128,24L32,56V112c0,56.16,38.4,108.8,96,120,57.6-11.2,96-63.84,96-120V56Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><polyline points="88 128 112 152 168 96" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "chat_dots": {
        "primary": '<path d="M40,56H216a8,8,0,0,1,8,8V176a8,8,0,0,1-8,8H152l-48,32V184H40a8,8,0,0,1-8-8V64A8,8,0,0,1,40,56Z" opacity="0.2"/>',
        "secondary": '<path d="M40,56H216a8,8,0,0,1,8,8V176a8,8,0,0,1-8,8H152l-48,32V184H40a8,8,0,0,1-8-8V64A8,8,0,0,1,40,56Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><circle cx="92" cy="120" r="8" fill="currentColor"/><circle cx="128" cy="120" r="8" fill="currentColor"/><circle cx="164" cy="120" r="8" fill="currentColor"/>',
    },
    "database": {
        "primary": '<ellipse cx="128" cy="56" rx="88" ry="32" opacity="0.2"/><path d="M40,168c0,17.68,39.4,32,88,32s88-14.32,88-32" opacity="0.2"/>',
        "secondary": '<ellipse cx="128" cy="56" rx="88" ry="32" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M40,56v48c0,17.68,39.4,32,88,32s88-14.32,88-32V56" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M40,104v48c0,17.68,39.4,32,88,32s88-14.32,88-32V104" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M40,152v48c0,17.68,39.4,32,88,32s88-14.32,88-32V152" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "magnifying_glass": {
        "primary": '<circle cx="116" cy="116" r="72" opacity="0.2"/>',
        "secondary": '<circle cx="116" cy="116" r="72" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><line x1="169.2" y1="169.2" x2="224" y2="224" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "target": {
        "primary": '<circle cx="128" cy="128" r="96" opacity="0.2"/><circle cx="128" cy="128" r="56" opacity="0.2"/>',
        "secondary": '<circle cx="128" cy="128" r="96" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><circle cx="128" cy="128" r="56" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><circle cx="128" cy="128" r="16" fill="currentColor"/>',
    },
    "bookmark": {
        "primary": '<path d="M184,32H72a8,8,0,0,0-8,8V232l64-40,64,40V40A8,8,0,0,0,184,32Z" opacity="0.2"/>',
        "secondary": '<path d="M184,32H72a8,8,0,0,0-8,8V232l64-40,64,40V40A8,8,0,0,0,184,32Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "warning_diamond": {
        "primary": '<path d="M220.24,119.76,136.24,35.76a12,12,0,0,0-17,0L35.76,119.76a12,12,0,0,0,0,17l84,84a12,12,0,0,0,17,0l83.52-83.52A12,12,0,0,0,220.24,119.76Z" opacity="0.2"/>',
        "secondary": '<path d="M220.24,119.76,136.24,35.76a12,12,0,0,0-17,0L35.76,119.76a12,12,0,0,0,0,17l84,84a12,12,0,0,0,17,0l83.52-83.52A12,12,0,0,0,220.24,119.76Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><line x1="128" y1="80" x2="128" y2="144" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><circle cx="128" cy="172" r="8" fill="currentColor"/>',
    },
    "presentation": {
        "primary": '<path d="M32,56H224a0,0,0,0,1,0,0V168a16,16,0,0,1-16,16H48a16,16,0,0,1-16-16V56A0,0,0,0,1,32,56Z" opacity="0.2"/>',
        "secondary": '<rect x="32" y="48" width="192" height="136" rx="8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><line x1="128" y1="184" x2="128" y2="216" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><polyline points="88 216 128 216 168 216" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><polyline points="80 140 108 112 148 140 176 100" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "lightning": {
        "primary": '<path d="M120,24l-64,104h48L88,232l96-120H136Z" opacity="0.2"/>',
        "secondary": '<path d="M120,24l-64,104h48L88,232l96-120H136Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "rocket": {
        "primary": '<path d="M170.6,136.4V56a8,8,0,0,0-8-8H93.4a8,8,0,0,0-8,8v80.4a54.3,54.3,0,0,0-24.8,52.2l2.5,20.1A8,8,0,0,0,71,216h25a54,54,0,0,0,10.6-32V172h42.8v12A54,54,0,0,0,160,216h25a8,8,0,0,0,7.9-7.3l2.5-20.1A54.3,54.3,0,0,0,170.6,136.4Z" opacity="0.2"/>',
        "secondary": '<path d="M128,112a16,16,0,1,0-16-16A16,16,0,0,0,128,112Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M170.6,136.4V56a8,8,0,0,0-8-8H93.4a8,8,0,0,0-8,8v80.4a54.3,54.3,0,0,0-24.8,52.2l2.5,20.1A8,8,0,0,0,71,216h25a54,54,0,0,0,10.6-32V172h42.8v12A54,54,0,0,0,160,216h25a8,8,0,0,0,7.9-7.3l2.5-20.1A54.3,54.3,0,0,0,170.6,136.4Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "compass": {
        "primary": '<circle cx="128" cy="128" r="96" opacity="0.2"/><path d="M160,96l-12,44-44,12,12-44Z" opacity="0.2"/>',
        "secondary": '<circle cx="128" cy="128" r="96" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M160,96l-12,44-44,12,12-44Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "arrow_right": {
        "primary": "",
        "secondary": '<line x1="40" y1="128" x2="216" y2="128" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><polyline points="176 88 216 128 176 168" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "check_circle": {
        "primary": '<circle cx="128" cy="128" r="96" opacity="0.2"/>',
        "secondary": '<circle cx="128" cy="128" r="96" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><polyline points="92 128 116 152 164 104" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
    "info": {
        "primary": '<circle cx="128" cy="128" r="96" opacity="0.2"/>',
        "secondary": '<circle cx="128" cy="128" r="96" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><line x1="128" y1="120" x2="128" y2="176" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><circle cx="128" cy="88" r="8" fill="currentColor"/>',
    },
    "download_simple": {
        "primary": "",
        "secondary": '<path d="M86,170.8,121.4,206a8.2,8.2,0,0,0,11.4,0L170,170.8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><line x1="128" y1="40" x2="128" y2="200" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/><path d="M48,176v32a8,8,0,0,0,8,8H200a8,8,0,0,0,8-8V176" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="12"/>',
    },
}


def icon(name: str, size: int = 24, color: str = "currentColor") -> str:
    """Return inline SVG HTML for a Phosphor duotone icon.

    Args:
        name: Icon name (use underscores, e.g. "shield_check")
        size: Icon size in pixels (default 24)
        color: CSS color value (default "currentColor")

    Returns:
        HTML string with inline SVG
    """
    entry = _ICONS.get(name)
    if entry is None:
        raise ValueError(
            f"Unknown icon: '{name}'. Available: {', '.join(sorted(_ICONS.keys()))}"
        )

    primary = entry.get("primary", "")
    secondary = entry.get("secondary", "")

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 256 256" '
        f'style="display:inline-block;vertical-align:middle;color:{color};flex-shrink:0;">'
        f'{primary}{secondary}</svg>'
    )


def icon_with_label(name: str, label: str, size: int = 24, color: str = "#6366f1") -> str:
    """Return icon + label wrapped in a flex container for sidebar use."""
    svg = icon(name, size=size, color=color)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'{svg}<span style="font-weight:500;color:#1e293b;">{label}</span></div>'
    )


# Convenience: all available icon names
AVAILABLE_ICONS = sorted(_ICONS.keys())
