import os
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from typing import List
from pydantic import SecretStr

from app.config.settings import settings


class LangChainService:
    """Service for LangChain operations with Google Gemini integration"""

    def __init__(self):
        self.openai_api_key = SecretStr(settings.OPENAI_API_KEY)
        self.openai_model = settings.OPENAI_MODEL or "gpt-4o-mini"

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key (OPENAI_API_KEY) is not set in the settings."
            )

        self._set_env_variables()

    def _set_env_variables(self):
        """Sets necessary environment variables to enable LangSmith tracing"""

        os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING or ""
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY or ""
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT or ""
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT or ""

    @lru_cache(maxsize=1)
    def get_openai_chat_model(self) -> ChatOpenAI:
        """Returns a cached instance of the OpenAI chat model."""
        return ChatOpenAI(
            model=self.openai_model,
            api_key=self.openai_api_key,
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
