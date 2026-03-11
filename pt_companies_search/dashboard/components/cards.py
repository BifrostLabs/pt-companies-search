import streamlit as st

def metric_card(title, value, subtitle=None, icon=None, delta=None):
    """
    Render a modern metric card using custom HTML/CSS.
    """
    delta_html = ""
    if delta:
        is_positive = "+" in str(delta) or "↑" in str(delta)
        delta_class = "positive" if is_positive else "negative"
        delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>'
    
    subtitle_html = f'<div style="font-size: 0.8rem; color: #8B949E; margin-top: 4px;">{subtitle}</div>' if subtitle else ''
    icon_html = f'<span>{icon}</span>' if icon else ''

    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{icon_html} {title}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def section_header(title, icon=None):
    """Render a styled section header."""
    icon_html = f'<span style="margin-right: 10px;">{icon}</span>' if icon else ''
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-top: 30px; margin-bottom: 20px;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #FAFAFA;">{icon_html}{title}</div>
            <div style="flex-grow: 1; height: 1px; background-color: #30363D; margin-left: 20px;"></div>
        </div>
    """, unsafe_allow_html=True)

def quick_action(icon, label, callback=None, key=None):
    """
    Render a quick action button.
    """
    if st.button(f"{icon} {label}", key=key, use_container_width=True):
        if callback:
            callback()

def timeline_event(title, timestamp, details=None, icon="📝"):
    """
    Render an event in a timeline.
    """
    st.markdown(f"""
        <div style="border-left: 2px solid #30363D; padding-left: 20px; padding-bottom: 24px; position: relative; margin-left: 10px;">
            <div style="position: absolute; left: -14px; top: 0; background: #0D1117; color: #58A6FF; border: 2px solid #30363D; border-radius: 50%; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-size: 14px;">{icon}</div>
            <div style="font-weight: 600; font-size: 0.95rem; color: #FAFAFA; line-height: 1.2;">{title}</div>
            <div style="font-size: 0.75rem; color: #8B949E; margin-top: 4px; margin-bottom: 8px; font-family: monospace;">{timestamp}</div>
            {f'<div style="font-size: 0.85rem; color: #C9D1D9; background: #161B22; padding: 10px; border-radius: 8px; border: 1px solid #30363D;">{details}</div>' if details else ''}
        </div>
    """, unsafe_allow_html=True)
