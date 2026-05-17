import os

MISTRAL_KEYS = {
    "orchestrator": os.environ["MISTRAL_KEY_ORCHESTRATOR"],
    "sql":          os.environ["MISTRAL_KEY_SQL"],
    "rag":          os.environ["MISTRAL_KEY_RAG"],
    "pdf":          os.environ["MISTRAL_KEY_PDF"],
}

def get_mistral_client(agent: str):
    from mistralai import Mistral
    return Mistral(api_key=MISTRAL_KEYS[agent])