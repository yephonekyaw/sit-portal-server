import os
from functools import lru_cache
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from typing import List
from pydantic import SecretStr

from app.config.settings import settings


class LangChainService:
    """Service for LangChain operations with Google Gemini integration"""

    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL

        self._set_env_variables()

    def _set_env_variables(self):
        """Sets necessary environment variables to enable LangSmith tracing"""

        os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING or ""
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY or ""
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT or ""
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT or ""

    @lru_cache(maxsize=1)
    def get_ollama_chat_model(self) -> ChatOllama:
        """Returns a cached instance of the Ollama chat model."""
        return ChatOllama(
            model=self.ollama_model,
            base_url=self.ollama_base_url,
            temperature=0.2,
        )

    def get_custom_prompt_template(
        self,
        input_variables: List[str],
        template: str,
    ) -> PromptTemplate:
        """Returns a custom prompt template with the provided variables."""
        return PromptTemplate(input_variables=input_variables, template=template)


def get_langchain_service() -> LangChainService:
    """Dependency to get LangChain service instance."""
    return LangChainService()
