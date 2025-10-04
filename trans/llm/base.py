# transgptex/llm/base.py
from abc import ABC, abstractmethod
from typing import List


class LLMBackend(ABC):
    """
    Abstract base class for LLM (Large Language Model) backends.
    This class defines the interface that all LLM implementations must follow
    to provide translation services for the LaTeX translation system.
    """

    @abstractmethod
    async def translate(self, text: str, target_lang: str) -> str:
        """
        Translate a single text segment to the target language.

        Args:
            text (str): The text segment to be translated
            target_lang (str): The target language for translation (e.g., 'Chinese', 'French', 'Spanish')

        Returns:
            str: The translated text
        """
        pass

    @abstractmethod
    async def translate_batch(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate multiple text segments in batch mode for efficiency.

        Args:
            texts (List[str]): List of text segments to be translated
            target_lang (str): The target language for translation

        Returns:
            List[str]: List of translated texts corresponding to the input texts
        """
        pass