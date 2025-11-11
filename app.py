import streamlit as st
from dotenv import find_dotenv, load_dotenv

from llm.prompts import INTRODUCTION_MESSAGE
from utils import (
    AUTHORS,
    LOGO_TEXT_DARK_URL,
    LOGO_TEXT_LIGHT_URL,
    LOGO_URL,
    QUERY_SUGGESTIONS,
    WARNING_MESSAGE,
    generate_response,
    initialize_clients,
    load_config,
)

# Load environment variables from the .env file.
load_dotenv(find_dotenv())


# Set Streamlit page configuration with custom title and icon.
st.set_page_config(page_title="Javne Nabavke AI", page_icon="⚖️")
st.title("Javne Nabavke AI")
st.divider()

# Initialize API clients for OpenAI and Qdrant and load configuration settings.
qdrant_client = initialize_clients()
config = load_config()

# Set default theme for logo selection
st.session_state.theme = "light"
logo_url = (
    LOGO_TEXT_DARK_URL if st.session_state.theme == "dark" else LOGO_TEXT_LIGHT_URL
)

# Set up the sidebar with logo and useful information
with st.sidebar:
    st.image(logo_url, width=200)
    st.divider()
    st.subheader("💡 Query Suggestions")
    with st.container(border=True, height=200):
        st.markdown(QUERY_SUGGESTIONS)

    st.subheader("⚠️ Warning")
    with st.container(border=True):
        st.markdown(WARNING_MESSAGE)

    st.subheader("✍️ Authors")
    st.markdown(AUTHORS)

# Main chat interface (removed Expert tab)
# Initialize or update the session state for storing chat messages.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": INTRODUCTION_MESSAGE}
    ]

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# Custom styling for the chat input uploader
st.markdown(
    """
    <style>
    div[data-testid="stChatInput"] > div:first-child {
        position: relative;
    }

    div[data-testid="stChatInput"] .chat-upload-slot {
        position: absolute;
        right: 3.75rem;
        bottom: 0.85rem;
        z-index: 10;
        display: flex;
        align-items: center;
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] {
        width: 38px;
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] section {
        padding: 0;
        border: none;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(49, 51, 63, 0.04);
        border-radius: 8px;
        box-shadow: inset 0 0 0 1px rgba(49, 51, 63, 0.15);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
        cursor: pointer;
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] section:hover {
        box-shadow: inset 0 0 0 1px rgba(49, 51, 63, 0.4);
        transform: translateY(-1px);
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] section svg {
        width: 16px;
        height: 16px;
        stroke: rgba(49, 51, 63, 0.7);
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] label {
        display: none;
    }

    div[data-testid="stChatInput"] .chat-upload-slot div[data-testid="stFileUploader"] button {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Upload control positioned next to the chat send arrow
st.markdown('<div class="chat-upload-slot">', unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Upload a file",
    type=["jpg", "jpeg", "png", "pdf"],
    label_visibility="collapsed",
    key="chat_file_uploader",
)
st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file is not None:
    existing_names = {file.name for file in st.session_state.uploaded_files}
    if uploaded_file.name not in existing_names:
        st.session_state.uploaded_files.append(uploaded_file)
        st.toast(f'Uploaded `{uploaded_file.name}`', icon="📄")

# Display all chat messages stored in the session state.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input and generate responses.
if prompt := st.chat_input("Pitanje za pravo..."):
    # Append user message to session state.
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat container.
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Generate a response using the LLM and display it as a stream.
        stream = generate_response(
            query=prompt,
            qdrant_client=qdrant_client,
            config=config,
        )
        # Write the response stream to the chat.
        response = st.write_stream(stream)

    # Append assistant's response to session state.
    st.session_state.messages.append({"role": "assistant", "content": response})
