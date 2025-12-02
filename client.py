import os

import streamlit as st
from qdrant_client import QdrantClient


@st.cache_resource
def initialize_clients() -> QdrantClient:
    """Initialize and return Qdrant client."""
    try:
        return QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
    except KeyError as e:
        raise EnvironmentError(f"Missing environment variable: {str(e)}")

