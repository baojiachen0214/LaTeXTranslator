# trans/llm/factory.py
from trans.config import get_config
from trans.llm.openai import OpenAILLM
from trans.llm.aliyun import AliyunLLM  # <-- Added import for Aliyun LLM
from trans.llm.generic import GenericLLM  # <-- Added import for Generic LLM
from trans.llm.base import LLMBackend

# Global instance variable to store the LLM backend instance
# This ensures singleton pattern - only one instance is created per session
_llm_instance: LLMBackend = None


def get_llm() -> LLMBackend:
    """
    Factory function to get the configured LLM backend instance.
    Uses singleton pattern to ensure only one instance is created.

    Returns:
        LLMBackend: Configured LLM backend instance
    """
    global _llm_instance
    if _llm_instance is None:
        # Load configuration to determine which backend to use
        cfg = get_config()

        # Initialize the appropriate LLM backend based on configuration
        if cfg.llm.backend == "openai":
            _llm_instance = OpenAILLM()
        elif cfg.llm.backend == "aliyun":  # <-- Added condition for Aliyun backend
            _llm_instance = AliyunLLM()
        elif cfg.llm.backend == "generic":  # <-- Added condition for Generic backend
            _llm_instance = GenericLLM()
        else:
            # Raise error if an unsupported backend is configured
            raise ValueError(f"Unsupported LLM backend: {cfg.llm.backend}")

    return _llm_instance