import json
import os
from typing import Dict, Generator, List

import streamlit as st
import yaml
from langfuse import observe
# from langfuse.decorators import langfuse_context  # Not available in this version
from langfuse.openai import openai
from loguru import logger
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from database.utils import SRPSKO_PRAVO_COLLECTION, embed_text, get_context, search
from llm.prompts import DEFAULT_CONTEXT
from llm.utils import formate_messages_chat
from router.query_router import formate_messages_router
from router.router_prompt import DEFAULT_ROUTER_RESPONSE

LOGO_URL = "assets/Logo.svg"
LOGO_TEXT_LIGHT_URL = "assets/Logo.svg"
LOGO_TEXT_DARK_URL = "assets/Logo.svg"
TEXT_URL = "assets/Legabot-Dark-Typography.svg"

WARNING_MESSAGE = """
⚠️ **Upozorenje**: Molimo imajte na umu da LegaBot može da pravi greške. Za kritične pravne informacije, uvek se konsultujte sa kvalifikovanim pravnim stručnjakom. LegaBot je tu da pomogne, a ne da zameni profesionalne pravne savete.
"""

QUERY_SUGGESTIONS = """
💡 **Predlozi za pitanja**: Možete me pitati o procedurama javnih nabavki, pravilima za izvođače, obavezama naručioca, ili bilo čemu drugom vezanom za zakone o javnim nabavkama.

Na koliko dana godisnjeg imam pravo?\n
Da li smem da koristim porodiljsko bolovanje zene umesto nje?\n
Koji porez placam ako sam preduzetnik?\n
Da li mogu da trazim da se izbrisu moji podaci sa sajta ako ih nisam odobrio?\n
U kom roku mogu da trazim zamenu proizvoda kojim nisam zadovoljan?\n
Kome pripadaju pokloni koje smo muz i ja dobili na vencanju?
"""

AUTHORS = """
[David Jovanovic](https://github.com/Scorge1990)
"""


class RouterConfig(BaseModel):
    model: str
    temperature: float


class ChatConfig(BaseModel):
    model: str
    temperature: float
    max_conversation: int


class EmbeddingsConfig(BaseModel):
    model: str
    dimensions: int


class OpenAIConfig(BaseModel):
    embeddings: EmbeddingsConfig
    chat: ChatConfig
    router: RouterConfig


class Config(BaseModel):
    openai: OpenAIConfig


def load_config(yaml_file_path: str = "./config.yaml") -> Config:
    with open(yaml_file_path, "r") as file:
        yaml_content = yaml.safe_load(file)
    return Config(**yaml_content)


@st.cache_resource
def initialize_clients() -> QdrantClient:
    """
    Initializes and returns the clients for OpenAI and Qdrant services.

    Returns:
    - Tuple[OpenAI, QdrantClient]: A tuple containing the initialized OpenAI and Qdrant clients.

    Raises:
    - EnvironmentError: If required environment variables are missing.
    """
    try:
        # Retrieve Qdrant client configuration from environment variables
        qdrant_url = os.environ["QDRANT_CLUSTER_URL"]
        qdrant_api_key = os.environ["QDRANT_API_KEY"]
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

        return qdrant_client
    except KeyError as e:
        error_msg = f"Missing environment variable: {str(e)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)


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
        # langfuse_context.update_current_trace(tags=collections)  # Not available in this version

        # Embed the user query using the specified model in the configuration
        embedding_response = embed_text(
            text=query,
            model=config.openai.embeddings.model,
        )
        embedding = embedding_response.data[0].embedding

        # Determine the context for the chat model based on the routed collections
        context = determine_context(collections, embedding, qdrant_client)

        # Generate the response stream from the chat model
        messages = formate_messages_chat(
            context=context, query=query, conversation=st.session_state.messages
        )
        stream = call_llm(
            model=config.openai.chat.model,
            temperature=config.openai.chat.temperature,
            messages=messages,
            stream=True,
        )

        # Yield each part of the response as it becomes available
        for chunk in stream:
            part = chunk.choices[0].delta.content
            if part is not None:
                yield part

        # langfuse_context.flush()  # Not available in this version

    except Exception as e:
        logger.error(f"An error occurred while generating the response: {str(e)}")
        yield "Sorry, an error occurred while processing your request."


def map_router_to_collection(router_name: str) -> str:
    """Map router response names to actual Qdrant collection names."""
    mapping = {
        "zakon_o_radu": "zakon_o_radu",
        "zakon_o_porezu_na_dohodak_gradjana": "zakon_o_porezu_na_dohodak_gradjana", 
        "zakon_o_zastiti_podataka_o_licnosti": "zakon_o_zastiti_podataka_o_licnosti",
        "zakon_o_zastiti_potrosaca": "zakon_o_zastiti_potrosaca",
        "porodicni_zakon": "porodicni_zakon",
        "pravne_konsultacije": "pravne_konsultacije",
        "index": "index",
        "paragraf_laws": "paragraf_laws",
        "carinski_zakon": "carinski_zakon_complete",
        "krivicni_zakonik": "krivicni_zakonik",
        "zakon_o_maloletnim_uciniocima_krivicnih_dela": "zakon_o_maloletnim_uciniocima_krivicnih_dela_i_krivicnopravnoj_zastiti_maloletnih_lica",
        "zakon_o_javnim_nabavkama": "paragraf_laws",
        "ustav_republike_srbije": "ustav_republike_srbije",
        "zakon_o_privrednim_drustvima": "zakon_o_privrednim_drustvima",
        "zakon_o_bankama": "zakon_o_bankama",
        "zakon_o_narodnoj_banci_srbije": "zakon_o_narodnoj_banci_srbije",
        "zakon_o_porezu_na_dodatu_vrednost": "zakon_o_porezu_na_dodatu_vrednost",
        "zakon_o_porezu_na_dobit_pravnih_lica": "zakon_o_porezu_na_dobit_pravnih_lica",
        "zakon_o_porezima_na_imovinu": "zakon_o_porezima_na_imovinu",
        "zakon_o_porezima_na_upotrebu_drzanje_i_nosenje_dobara": "zakon_o_porezima_na_upotrebu_drzanje_i_nosenje_dobara",
        "zakon_o_planiranju_i_izgradnji": "zakon_o_planiranju_i_izgradnji",
        "zakon_o_bezbednosti_i_zdravlju_na_radu": "zakon_o_bezbednosti_i_zdravlju_na_radu",
        "zakon_o_evidencijama_u_oblasti_rada": "zakon_o_evidencijama_u_oblasti_rada",
        "zakon_o_izvrsenju_krivicnih_sankcija": "zakon_o_izvrsenju_krivicnih_sankcija",
        "zakon_o_javnim_agencijama": "zakon_o_javnim_agencijama",
        "zakon_o_javnim_medijskim_servisima": "zakon_o_javnim_medijskim_servisima",
        "zakon_o_javnim_preduzecima": "zakon_o_javnim_preduzecima",
        "zakon_o_javnim_sluzbama": "zakon_o_javnim_sluzbama",
        "zakon_o_javnim_skijalistima": "zakon_o_javnim_skijalistima",
        "zakon_o_komorama_zdravstvenih_radnika": "zakon_o_komorama_zdravstvenih_radnika",
        "zakon_o_mirnom_resavanju_radnih_sporova": "zakon_o_mirnom_resavanju_radnih_sporova",
        "zakon_o_naknadama_za_koriscenje_javnih_dobara": "zakon_o_naknadama_za_koriscenje_javnih_dobara",
        "zakon_o_posebnim_ovlascenjima_radi_efikasne_zastite_prava_intelektualne_svojine": "zakon_o_posebnim_ovlascenjima_radi_efikasne_zastite_prava_intelektualne_svojine",
        "zakon_o_saradnji_sa_medjunarodnim_krivicnim_sudom": "zakon_o_saradnji_sa_medjunarodnim_krivicnim_sudom",
        "zakon_o_sedistima_i_podrucjima_sudova_i_javnih_tuzilastava": "zakon_o_sedistima_i_podrucjima_sudova_i_javnih_tuzilastava",
        "zakon_o_uslovima_izgradnje_stanova_za_pripadnike_snaga_bezbednosti": "zakon_o_uslovima_izgradnje_stanova_za_pripadnike_snaga_bezbednosti",
        "zakon_o_uslovima_za_upucivanje_zaposlenih_na_privremeni_rad_u_inostranstvo_i_njihovoj_zastiti": "zakon_o_uslovima_za_upucivanje_zaposlenih_na_privremeni_rad_u_inostranstvo_i_njihovoj_zastiti",
        "zakon_o_platama_u_drzavnim_organima_i_javnim_sluzbama": "zakon_o_platama_u_drzavnim_organima_i_javnim_sluzbama",
        "zakon_o_privatnom_obezbedjenju": "zakon_o_privatnom_obezbedjenju",
        "zakon_o_zastiti_korisnika_finansijskih_usluga": "zakon_o_zastiti_korisnika_finansijskih_usluga",
        "pravilnik_o_aerosolnim_rasprasivacima": "paragraf_laws",
        "pravilnik_o_areometrima": "paragraf_laws",
        "zakon_o_zvanicnoj_statistici": "zakon_o_zvanicnoj_statistici",
        "zakon_o_regionalnom_razvoju": "zakon_o_regionalnom_razvoju",
        "zakon_o_glavnom_gradu": "zakon_o_glavnom_gradu",
        "sporazum_francuska_dvostruko_oporezivanje": "zakon_o_ratifikaciji_sporazuma_izmedju_socijalisticke_federativne_republike_jugoslavije_i_republike_francuske_o_izbegavanju_dvostrukog_oporezivanja_u_oblasti_poreza_na_dohodak_sa_protokolom",
        "eticki_kodeks_javnih_izvrsitelja": "eticki_kodeks_javnih_izvrsitelja",
        "porodicni_zakon": "porodicni_zakon",
        "zakon_o_osnovama_svojinskopravnih_odnosa": "zakon_o_osnovama_svojinskopravnih_odnosa",
        "dinarska_vrednost_evropskih_pragova": "dinarska_vrednost_evropskih_pragova",
        "naredba_o_merama_postupanja_u_cilju_unistavanja_unete_alohtone_divlje_vrste_heracleum_sosnowskyi": "naredba_o_merama_postupanja_u_cilju_unistavanja_unete_alohtone_divlje_vrste_heracleum_sosnowskyi",
        "nema_zakona": "nema_zakona"
    }
    return mapping.get(router_name, router_name)


def determine_context(
    collections: List[str], embedding: List[float], qdrant_client: QdrantClient
) -> str:
    """Determines the context for generating responses based on search results from collections."""
    try:
        if collections[0] == DEFAULT_ROUTER_RESPONSE:
            return DEFAULT_CONTEXT

        if not qdrant_client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
            logger.error(
                f'Target collection "{SRPSKO_PRAVO_COLLECTION}" does not exist in Qdrant.'
            )
            return DEFAULT_CONTEXT

        search_results: List = []
        for router_name in collections:
            law_name = map_router_to_collection(router_name)
            if law_name in {DEFAULT_ROUTER_RESPONSE, "nema_zakona"}:
                continue

            search_limit = 20 if law_name == "pravne_konsultacije" else 10
            try:
                results = search(
                    client=qdrant_client,
                    collection=SRPSKO_PRAVO_COLLECTION,
                    query_vector=embedding,
                    limit=search_limit,
                    with_vectors=True,
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="law_name",
                                match=MatchValue(value=law_name),
                            )
                        ]
                    ),
                )
                if results:
                    logger.info(
                        f"Found {len(results)} results for {law_name} "
                        f'in collection "{SRPSKO_PRAVO_COLLECTION}".'
                    )
                search_results.extend(results)
            except Exception as exc:
                logger.error(
                    f"Error searching law {law_name} in "
                    f'collection "{SRPSKO_PRAVO_COLLECTION}": {exc}'
                )
                continue

        if not search_results:
            logger.warning(
                "No relevant vectors retrieved for routed laws. "
                "Falling back to default context."
            )
            return DEFAULT_CONTEXT

        top_k = 20 if len(collections) > 1 else 15
        return get_context(search_results=search_results, top_k=top_k)
    except Exception as e:
        logger.error(f"Error determining context: {str(e)}")
        return DEFAULT_CONTEXT  # Fallback to default context
