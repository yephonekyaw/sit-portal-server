from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from typing import List

from app.config.settings import settings


class LangChainService:
    """Service for LangChain operations with Google Gemini integration"""
    
    def __init__(self):
        self.google_api_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL or "gemini-2.5-flash"

        if not self.google_api_key:
            raise ValueError(
                "Google API key (GEMINI_API_KEY) is not set in the settings."
            )

    @lru_cache(maxsize=1)
    def get_gemini_chat_model(self) -> ChatGoogleGenerativeAI:
        """Returns a cached instance of the Google Gemini chat model."""
        return ChatGoogleGenerativeAI(
            model=self.gemini_model,
            google_api_key=self.google_api_key,
            temperature=0.2,
        )

    def get_custom_prompt_template(
        self,
        input_variables: List[str],
        template: str,
    ) -> PromptTemplate:
        """Returns a custom prompt template with the provided variables."""
        return PromptTemplate(input_variables=input_variables, template=template)