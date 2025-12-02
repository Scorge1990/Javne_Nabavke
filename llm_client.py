from typing import Dict, List

from langfuse import observe
from langfuse.openai import openai
from openai.types.chat import ChatCompletion


@observe(as_type="generation")
def call_llm(
    model: str,
    temperature: float,
    messages: List[Dict],
    json_response: bool = False,
    stream: bool = False,
) -> ChatCompletion:
    """
    Get an answer from the OpenAI chat model.

    Args:
        model (str): The model name to use.
        temperature (float): The temperature setting for the model.
        messages (List[Dict]): The list of messages to send to the model.
        stream (bool, optional): Whether to stream the response. Defaults to False.

    Returns:
        ChatCompletion: The chat completion response from OpenAI.
    """
    return openai.chat.completions.create(
        model=model,
        response_format={"type": "json_object"} if json_response else None,
        temperature=temperature,
        messages=messages,
        stream=stream,
    )


