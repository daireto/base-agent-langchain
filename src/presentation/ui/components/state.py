import streamlit as st
from langchain_core.messages import BaseMessage

from services.agent_service import AgentToolInterrupt


def init_session_state(
    messages: list[BaseMessage],
    interrupts: list[AgentToolInterrupt],
) -> None:
    defaults = {
        'messages': messages,
        'interrupts': interrupts,
        'interrupt_decisions': {},
        'apply_interrupt_decisions': False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
