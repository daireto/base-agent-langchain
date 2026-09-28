import asyncio

import streamlit as st
from langchain_core.messages import HumanMessage
from uuid_utils.compat import uuid7

from dtos.agent import AgentInput
from presentation.ui.components.agent_runtime import get_runtime
from presentation.ui.components.chat import (
    render_human,
    render_messages,
    render_streamed_ai,
)
from presentation.ui.components.interrupts import (
    get_interrupt_commands,
    render_interrupts,
)
from presentation.ui.components.sidebar import render_sidebar
from presentation.ui.components.state import (
    init_state,
    reset_state,
    set_messages_and_interrupts,
)
from services.agent_service import AgentRequest

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

    thread_id = st.session_state.thread_id or uuid7()

    request = AgentRequest(
        input=AgentInput(
            query=prompt,
        ),
        thread_id=thread_id,
    )
    stream = runtime.stream(request)
    render_streamed_ai(stream)

    if not st.session_state.thread_id:
        st.session_state.thread_id = thread_id
        st.session_state.conversations = runtime.get_conversations()
        st.rerun()


def process_interrupts() -> None:
    if not st.session_state.thread_id or not st.session_state.apply_interrupt_decisions:
        return

    if not st.session_state.interrupts:
        st.session_state.apply_interrupt_decisions = False
        return

    commands = get_interrupt_commands()
    request = AgentRequest(
        input=AgentInput(query='', commands=commands),
        thread_id=st.session_state.thread_id,
    )
    stream = runtime.stream(request)
    render_streamed_ai(stream)

    st.session_state.apply_interrupt_decisions = False


def run() -> None:
    init_state()

    st.set_page_config(layout='wide', page_title='LangGraph Agent')

    if st.session_state.thread_id:
        set_messages_and_interrupts(runtime)

    st.session_state.conversations = runtime.get_conversations()

    on_reset, selected_thread_id, deleted_thread_id = render_sidebar()

    if on_reset:
        reset_state()
        st.rerun()

    if selected_thread_id:
        st.session_state.thread_id = selected_thread_id
        set_messages_and_interrupts(runtime)

    if deleted_thread_id:
        runtime.clean_state(deleted_thread_id)
        runtime.delete_conversation(deleted_thread_id)
        if st.session_state.thread_id == deleted_thread_id:
            reset_state()
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
