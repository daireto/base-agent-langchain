from typing import TYPE_CHECKING

import streamlit as st
from uuid_utils.compat import UUID

if TYPE_CHECKING:
    from persistence.models import Conversation


def render_sidebar() -> tuple[bool, UUID | None, UUID | None]:
    with st.sidebar:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] button p {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.title('Conversaciones')

        return_value = (False, None, None)

        if pressed := st.button('Nueva conversación', type='primary'):
            return pressed, None, None

        conversations: list[Conversation] = st.session_state.conversations
        for conversation in conversations:
            select_col, delete_col = st.columns([8, 1])
            with select_col:
                title = conversation.title or 'Sin título'
                if st.button(
                    title,
                    key=f'select-{conversation.id}',
                    use_container_width=True,
                    help=title,
                ):
                    return_value = (False, conversation.id, None)
            with delete_col:
                if st.button(
                    '',
                    icon=':material/delete:',
                    key=f'delete-{conversation.id}',
                    help='Eliminar conversación',
                ):
                    return_value = (False, None, conversation.id)

        return return_value
