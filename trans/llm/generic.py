# trans/llm/generic.py
import asyncio
import os
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI, APIError
from trans.config import get_config
from trans.llm.base import LLMBackend
from trans.utils.logger import logger


class GenericLLM(LLMBackend):
    """
    Generic LLM backend implementation using the OpenAI-compatible API format.
    This class provides integration with any LLM API that follows the OpenAI API specification,
    including OpenAI, Azure OpenAI, Anthropic Claude (via proxy), Google Gemini (via proxy), etc.
    """

    def __init__(self):
        """
        Initialize the Generic LLM backend with configuration parameters.
        """
        # Load configuration from the system
        cfg = get_config()

        # Get API key from direct config or environment variable
        api_key_val = cfg.llm.api_key or os.environ.get(cfg.llm.api_key_env)
        if not api_key_val:
            # Raise error if API key is not found in environment
            raise ValueError(f"API key not found in config or environment variable: {cfg.llm.api_key_env}")

        # Initialize the AsyncOpenAI client with API key and base URL
        self.client = AsyncOpenAI(api_key=api_key_val, base_url=cfg.llm.base_url)

        # Create semaphore to limit concurrent API calls based on configuration
        self.semaphore = asyncio.Semaphore(cfg.llm.max_concurrent)

        # Store maximum retry attempts from configuration
        self.max_retries = cfg.llm.max_retries

        # Store model from configuration
        self.model = cfg.llm.model
        
        # Store other parameters
        self.temperature = cfg.llm.temperature
        self.top_p = cfg.llm.top_p

    async def translate(self, text: str, target_lang: str) -> str:
        """
        Translate a single text segment to the target language using the generic API.

        Args:
            text (str): Text to be translated
            target_lang (str): Target language for translation

        Returns:
            str: Translated text, or original text if translation fails
        """
        # Load configuration for system prompt and other parameters
        cfg = get_config()

        # System prompt that instructs the LLM on LaTeX translation rules
        system_prompt = f"You are a professional LaTeX translator. Your task is to translate the following text from English to {target_lang}. CRITICAL RULES: 1. Preserve ALL LaTeX commands (e.g., \\section{{}}, \\cite{{}}, \\ref{{}}, \\begin{{equation}}, \\end{{equation}}, $...$, $$...$$) EXACTLY as they are. Do not translate the content inside {{}} of commands. 2. Do not translate mathematical formulas, variable names, or code snippets. 3. Maintain the original structure and formatting as much as possible. 4. Do not translate special placeholders like `__TGTEX_...__`. 5. Ensure the output is valid LaTeX that compiles correctly."

        # User prompt that provides the specific text to translate
        user_prompt = f"Translate the following source text to {target_lang}. Remember: Preserve LaTeX commands and structure!\n\nSource Text:\n{text}\n\nTranslated Text:"

        # Attempt translation with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                # Use semaphore to limit concurrent API calls
                async with self.semaphore:
                    # Make the API call to the generic OpenAI-compatible API
                    completion = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},  # System instruction
                            {"role": "user", "content": user_prompt}  # User request
                        ],
                        temperature=self.temperature,
                        top_p=self.top_p,
                        max_tokens=4096,  # Maximum tokens for the response
                    )
                    # Return the content of the first choice in the response
                    return completion.choices[0].message.content

            except APIError as e:
                # Log warning for API errors and implement retry logic
                logger.warning(f"Attempt {attempt + 1} failed for a chunk: {e}")

                # Handle retryable errors (rate limits, server errors)
                if e.status_code in [429, 502, 503]:
                    if attempt < self.max_retries:
                        # Exponential backoff before retry
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        logger.error(f"All retries failed for a chunk. Returning original text.")
                        return text
                else:
                    # Handle non-retryable errors
                    logger.error(f"Non-retryable error for a chunk: {e}. Returning original text.")
                    return text
            except Exception as e:
                # Handle any other unexpected errors
                logger.error(f"Unexpected error during translation: {e}. Returning original text.")
                return text
        return text

    async def translate_batch(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate multiple text segments in batch mode using concurrent API calls.

        Args:
            texts (List[str]): List of texts to be translated
            target_lang (str): Target language for translation

        Returns:
            List[str]: List of translated texts corresponding to the input texts
        """
        # Create async tasks for each text translation
        tasks = [self.translate(text, target_lang) for text in texts]

        # Execute all tasks concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handling any exceptions that occurred
        processed_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                # Log error if translation failed and fallback to original text
                logger.error(f"Error processing batch item {i}: {res}")
                processed_results.append(texts[i])  # Fallback to original text
            else:
                # Add successful translation result
                processed_results.append(res)
        return processed_results