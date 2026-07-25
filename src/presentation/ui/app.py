import asyncio

import streamlit as st
from langchain_core.messages import HumanMessage

from dtos.agent import AgentInput
from presentation.ui.components.chat import (
    render_human,
    render_messages,
    render_streamed_ai,
)
from presentation.ui.components.interrupts import (
    get_interrupt_commands,
    render_interrupts,
)
from presentation.ui.components.runtime import get_runtime
from presentation.ui.components.sidebar import render_sidebar
from presentation.ui.components.state import init_session_state
from services.agent_service import AgentConfig, AgentRequest
from utils.uuid import uuid7

USER_ID = '123'
CHAT_ID = '456'
THREAD_ID = uuid7()
CONFIG_REQUEST = AgentConfig(thread_id=THREAD_ID)

runtime = get_runtime()


def run_async(coro):  # noqa: ANN001, ANN201
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    return loop.run_until_complete(coro)


def process_user_message(prompt: str) -> None:
    human = HumanMessage(content=prompt)
    st.session_state.messages.append(human)
    render_human(human)

    request = AgentRequest(
        input=AgentInput(
            query=prompt,
        ),
        thread_id=THREAD_ID,
    )
    stream = runtime.stream(request)
    render_streamed_ai(stream)


def process_interrupts() -> None:
    if not st.session_state.apply_interrupt_decisions:
        return

    if not st.session_state.interrupts:
        st.session_state.apply_interrupt_decisions = False
        return

    commands = get_interrupt_commands()
    request = AgentRequest(
        input=AgentInput(query='', commands=commands),
        thread_id=THREAD_ID,
    )
    stream = runtime.stream(request)
    render_streamed_ai(stream)

    st.session_state.apply_interrupt_decisions = False


def run() -> None:
    st.set_page_config(layout='wide', page_title='LangGraph Agent')

    state = runtime.get_state(CONFIG_REQUEST)
    state_response = runtime.parse_state_to_response(state)

    init_session_state(
        messages=state_response.messages,
        interrupts=state_response.interrupts,
    )

    on_clean = render_sidebar()

    if on_clean:
        runtime.clean_state(THREAD_ID)
        st.session_state.messages.clear()
        st.session_state.interrupts.clear()
        st.rerun()

    col1, col2 = st.columns([2, 1])

    with col1:
        chat_container = st.container()
        with chat_container:
            render_messages()
            process_interrupts()

        if prompt := st.chat_input('Escribe un mensaje...'):
            with chat_container:
                process_user_message(prompt)

    with col2:
        render_interrupts()


if __name__ == '__main__':
    run()
