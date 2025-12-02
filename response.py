import json
from typing import Generator

import streamlit as st
from langfuse import observe
from loguru import logger
from openai import RateLimitError
from qdrant_client import QdrantClient

from config import Config
from context import determine_context
from database.utils import embed_text
from llm.utils import formate_messages_chat
from llm_client import call_llm
from router.query_router import formate_messages_router


@observe()
def generate_response(
    query: str, qdrant_client: QdrantClient, config: Config
) -> Generator[str, None, None]:
    """
    Generates a response for a given user query using a combination of semantic search and a chat model.

    Args:
    - query (str): The user's query string.
    - qdrant_client (QdrantClient): Client to interact with Qdrant's API.
    - config (Config): Configuration settings for API interaction and response handling.

    Yields:
    - str: Parts of the generated response from the chat model.
    """
    try:
        # Limit the stored messages to the maximum conversation length defined in the configuration
        st.session_state.messages = st.session_state.messages[
            -config.openai.chat.max_conversation :
        ]

        # Determine the relevant collections to route the query to
        messages = formate_messages_router(query)
        response = call_llm(
            model=config.openai.router.model,
            temperature=config.openai.router.temperature,
            messages=messages,
            json_response=True,
        )
        collections = json.loads(response.choices[0].message.content)["response"]
        logger.info(f"Query routed to collections: {collections}")

        # Embed the user query using the specified model in the configuration
        embedding_response = embed_text(
            text=query,
            model=config.openai.embeddings.model,
        )
        embedding = embedding_response.data[0].embedding

        # Determine the context for the chat model based on the routed collections
        context = determine_context(collections, embedding, qdrant_client, original_query=query)

        # Convert conversation history from message dicts to string format
        conversation_history = []
        for msg in st.session_state.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                conversation_history.append(f"Korisnik: {content}")
            elif role == "assistant":
                conversation_history.append(f"Asistent: {content}")
        
        # Generate the response stream from the chat model
        messages = formate_messages_chat(
            context=context, query=query, conversation=conversation_history
        )
        stream = call_llm(
            model=config.openai.chat.model,
            temperature=config.openai.chat.temperature,
            messages=messages,
            stream=True,
        )

        # Yield each part of the response as it becomes available
        for chunk in stream:
            try:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and hasattr(delta, 'content'):
                        part = delta.content
                        if part is not None:
                            yield part
            except Exception as chunk_error:
                logger.warning(f"Error processing chunk: {chunk_error}")
                continue

    except RateLimitError as e:
        error_str = str(e)
        logger.error(f"OpenAI rate limit/quota error: {error_str}")
        if "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
            yield "Izvinjavam se, ali trenutno je dostignut limit za OpenAI API. Molimo vas da proverite vaš plan i naplatu na OpenAI platformi (https://platform.openai.com/account/billing). Pokušajte ponovo kasnije kada se limit resetuje."
        else:
            yield "Izvinjavam se, ali trenutno je dostignut limit zahteva. Molimo vas da sačekate nekoliko trenutaka i pokušate ponovo."
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in router response: {str(e)}")
        yield "Sorry, an error occurred while processing your request. Please try again."
    except KeyError as e:
        logger.error(f"Missing key in response: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        yield "Sorry, an error occurred while processing your request. Please try again."
    except AttributeError as e:
        logger.error(f"Attribute error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        yield "Sorry, an error occurred while processing your request. Please try again."
    except Exception as e:
        error_str = str(e)
        logger.error(f"An error occurred while generating the response: {error_str}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Check for OpenAI quota/rate limit errors in generic exception
        if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
            yield "Izvinjavam se, ali trenutno je dostignut limit za OpenAI API. Molimo vas da proverite vaš plan i naplatu na OpenAI platformi. Pokušajte ponovo kasnije."
        elif "rate limit" in error_str.lower() or "rate_limit" in error_str.lower():
            yield "Izvinjavam se, ali trenutno je dostignut limit zahteva. Molimo vas da sačekate nekoliko trenutaka i pokušate ponovo."
        else:
            yield "Sorry, an error occurred while processing your request."

