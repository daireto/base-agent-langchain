import json
from collections.abc import Generator

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolCall, ToolMessage

from dtos.agent import AgentResponse
from dtos.common import SSEEvent


def friendly_tool_call_msg(name: str) -> str:
    if name.endswith('_agent_tool'):
        agent = name[:-11]
        return f'🤖 Invocando agente de {agent}'

    return f'🛠️ Invocando {name}'


def friendly_tool_message_msg(name: str) -> str:
    if name.endswith('_agent_tool'):
        agent = name[:-11]
        return f'🤖 Respuesta del agente de {agent}'

    return f'🛠️ Respuesta de {name}'


def render_tool_call(tool_call: ToolCall) -> None:
    if not tool_call['name']:
        return

    title = friendly_tool_call_msg(tool_call['name'])

    with st.status(
        title,
        state='running',
        expanded=False,
    ):
        st.code(
            json.dumps(
                tool_call['args'],
                indent=2,
                ensure_ascii=False,
            ),
            language='json',
        )


def render_tool(tool_message: ToolMessage) -> None:
    if not tool_message.name:
        return

    with st.chat_message('assistant'):
        title = friendly_tool_message_msg(tool_message.name)
        with st.status(
            title,
            state='complete',
            expanded=False,
        ):
            st.markdown(str(tool_message.content))


def render_human(message: HumanMessage) -> None:
    with st.chat_message('user'):
        st.markdown(str(message.content))


def render_ai(message: AIMessage) -> None:
    tool_calls = [t for t in message.tool_calls if t['name']]
    if tool_calls:
        with st.chat_message('assistant'):
            for tool_call in tool_calls:
                render_tool_call(tool_call)

    if message.content:
        with st.chat_message('assistant'):
            st.markdown(str(message.content))


def render_streamed_ai(stream: Generator[SSEEvent[AgentResponse]]) -> None:  # noqa: C901
    interrupts = None
    full_text = ''
    reset_full_text = False
    ai_msg_container = None
    placeholder = None

    for event in stream:
        if event.event == 'end':
            interrupts = event.data.interrupts
            st.session_state.messages.append(event.data.message)
            break

        if isinstance(event.data.message, ToolMessage):
            st.session_state.messages.append(event.data.message)
            render_tool(event.data.message)
        elif isinstance(event.data.message, AIMessage):
            tool_calls = [t for t in event.data.message.tool_calls if t['name']]
            if tool_calls:
                reset_full_text = True
                st.session_state.messages.append(event.data.message)
                with st.chat_message('assistant'):
                    for tool_call in tool_calls:
                        render_tool_call(tool_call)
            elif event.data.message.content:
                if reset_full_text:
                    full_text = ''
                    reset_full_text = False

                if ai_msg_container is None:
                    ai_msg_container = st.chat_message('assistant')

                with ai_msg_container:
                    if placeholder is None:
                        placeholder = st.empty()

                    full_text += str(event.data.message.content)
                    placeholder.markdown(full_text)

    if interrupts:
        with st.chat_message('assistant'):
            st.markdown(event.data.message.content)
        st.session_state.interrupts = interrupts
    else:
        st.session_state.interrupts.clear()
        st.session_state.interrupt_decisions.clear()


def render_messages() -> None:
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            render_human(message)
        elif isinstance(message, ToolMessage):
            render_tool(message)
        elif isinstance(message, AIMessage):
            render_ai(message)
