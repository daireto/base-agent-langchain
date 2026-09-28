from copy import deepcopy

import streamlit as st

from dtos.agent import AgentConfig
from presentation.ui.components.agent_runtime import AgentRuntime

DEFAULTS = {
    'thread_id': None,
    'conversations': [],
    'messages': [],
    'interrupts': [],
    'interrupt_decisions': {},
    'apply_interrupt_decisions': False,
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, deepcopy(value))


def reset_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = deepcopy(value)


def set_messages_and_interrupts(runtime: AgentRuntime) -> None:
    messages = runtime.get_lc_messages(st.session_state.thread_id)
    config_request = AgentConfig(thread_id=st.session_state.thread_id)
    state = runtime.get_state(config_request)
    state_response = runtime.parse_state_to_response(state)
    st.session_state.interrupts = state_response.interrupts
    st.session_state.messages = messages
