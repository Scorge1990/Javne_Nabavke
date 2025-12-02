import streamlit as st
from dotenv import find_dotenv, load_dotenv

from llm.prompts import INTRODUCTION_MESSAGE
from constants import AUTHORS, LOGO_TEXT_LIGHT_URL, QUERY_SUGGESTIONS, WARNING_MESSAGE
from client import initialize_clients
from config import load_config
from response import generate_response

load_dotenv(find_dotenv())

st.set_page_config(page_title="Javne Nabavke AI", page_icon="⚖️")
st.title("Javne Nabavke AI")
st.divider()

qdrant_client = initialize_clients()
config = load_config()

with st.sidebar:
    st.image(LOGO_TEXT_LIGHT_URL, width=200)
    st.divider()
    st.subheader("💡 Query Suggestions")
    with st.container(border=True, height=200):
        st.markdown(QUERY_SUGGESTIONS)

    st.subheader("⚠️ Warning")
    with st.container(border=True):
        st.markdown(WARNING_MESSAGE)

    st.subheader("✍️ Authors")
    st.markdown(AUTHORS)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": INTRODUCTION_MESSAGE}
    ]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pitanje za pravo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = generate_response(query=prompt, qdrant_client=qdrant_client, config=config)
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
