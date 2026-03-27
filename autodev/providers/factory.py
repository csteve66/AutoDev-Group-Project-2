from __future__ import annotations

import os

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from autodev.config import Settings


def build_chat_model(settings: Settings):
    if settings.provider.lower() == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when AUTODEV_PROVIDER=groq")
        model = os.getenv("GROQ_MODEL", settings.model)
        return ChatGroq(model=model, api_key=api_key, temperature=0)

    return ChatOllama(model=settings.model, temperature=0)
