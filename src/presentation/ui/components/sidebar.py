import streamlit as st


def render_sidebar() -> bool:
    with st.sidebar:
        st.title('Configuración')

        return st.button('Reiniciar conversación')
