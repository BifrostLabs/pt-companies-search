import streamlit as st

def metric_card(title, value, subtitle=None, icon=None, delta=None):
    """
    Render a modern metric card.
    """
    st.markdown(f"""
        <div style="background-color: #1A1D24; border: 1px solid #30363D; border-radius: 10px; padding: 20px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="font-size: 14px; color: #8B949E; margin-bottom: 8px;">{icon if icon else ''} {title}</div>
            <div style="font-size: 28px; font-weight: 700; color: #FAFAFA;">{value}</div>
            {f'<div style="font-size: 12px; color: #3FB950; margin-top: 4px;">{delta}</div>' if delta else ''}
            {f'<div style="font-size: 12px; color: #8B949E; margin-top: 4px;">{subtitle}</div>' if subtitle else ''}
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
        <div style="border-left: 2px solid #30363D; padding-left: 20px; padding-bottom: 20px; position: relative;">
            <div style="position: absolute; left: -9px; top: 0; background: #0D1117; color: #58A6FF; border-radius: 50%; padding: 4px;">{icon}</div>
            <div style="font-weight: 600; font-size: 14px; color: #FAFAFA;">{title}</div>
            <div style="font-size: 11px; color: #8B949E; margin-bottom: 4px;">{timestamp}</div>
            {f'<div style="font-size: 13px; color: #C9D1D9;">{details}</div>' if details else ''}
        </div>
    """, unsafe_allow_html=True)
