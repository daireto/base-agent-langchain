import json

import streamlit as st

from dtos.agent import AgentInterruptEditedAction
from services.agent_service import AgentInterruptCommand, AgentToolInterrupt


def render_json_editor(key: str) -> None:
    value = st.session_state.interrupt_decisions[key]['args']
    text = st.text_area(
        'Args',
        value=json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        ),
        height=180,
        key=f'json_{key}',
    )

    try:
        st.session_state.interrupt_decisions[key]['args'] = json.loads(text)
    except Exception:
        st.error('JSON inválido')


def render_interrupt(interrupt: AgentToolInterrupt) -> None:
    key = interrupt.name

    decisions = st.session_state.interrupt_decisions
    if key not in decisions:
        decisions[key] = {
            'decision': interrupt.allowed_decisions[0],
            'args': interrupt.args,
            'reason': '',
        }
    state = decisions[key]

    with st.container(border=True):
        st.subheader(interrupt.name)
        st.caption(interrupt.description)

        decision = st.selectbox(
            'Decisión',
            interrupt.allowed_decisions,
            key=f'decision_{key}',
            index=interrupt.allowed_decisions.index(state['decision']),
        )

        state['decision'] = decision

        if decision == 'edit':
            render_json_editor(key)

        elif decision == 'reject':
            state['reason'] = st.text_area(
                'Razón del rechazo',
                value=state['reason'],
                key=f'reason_{key}',
            )


def render_interrupts() -> None:
    st.subheader('Human Review')

    if not st.session_state.interrupts:
        st.info('No hay interrupciones')
        return

    for interrupt in st.session_state.interrupts:
        render_interrupt(interrupt)

    if st.button('Aplicar decisiones'):
        st.session_state.apply_interrupt_decisions = True
        st.rerun()


def get_interrupt_commands() -> dict[str, AgentInterruptCommand]:
    return {
        i.name: AgentInterruptCommand(
            decision=st.session_state.interrupt_decisions[i.name]['decision'],
            edited_action=AgentInterruptEditedAction(
                name=i.name,
                args=st.session_state.interrupt_decisions[i.name]['args'],
            ),
            reject_reason=st.session_state.interrupt_decisions[i.name]['reason'],
        )
        for i in st.session_state.interrupts
    }
