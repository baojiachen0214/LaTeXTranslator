# trans/llm/aliyun.py
import asyncio
import os
from typing import List
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role
from trans.config import get_config
from trans.llm.base import LLMBackend
from trans.utils.logger import logger


class AliyunLLM(LLMBackend):
    """
    Aliyun LLM backend implementation using DashScope API.
    This class provides integration with Alibaba Cloud's DashScope service for LaTeX translation.
    """

    def __init__(self):
        """
        Initialize the Aliyun LLM backend with configuration parameters.
        """
        # Load configuration from the system
        cfg = get_config()

        # Aliyun uses api_key field (i.e., DashScope API Key)
        if cfg.llm.api_key:
            self.api_key = cfg.llm.api_key
        else:
            # Can also read from environment variable DASHSCOPE_API_KEY, which is the default behavior of dashscope SDK
            self.api_key = os.environ.get("DASHSCOPE_API_KEY")

        # Validate that API key is available
        if not self.api_key:
            raise ValueError(
                "Aliyun LLM requires an API key. Please set 'api_key' in config or 'DASHSCOPE_API_KEY' in environment variables.")

        # Initialize model parameters from configuration
        self.model = cfg.llm.model
        self.temperature = cfg.llm.temperature
        self.top_p = cfg.llm.top_p
        self.max_retries = cfg.llm.max_retries

    async def _call_api(self, messages: List[dict]) -> str:
        """
        Synchronously call the dashscope API and wrap it as async.
        This method handles API calls with retry logic and error handling.

        Args:
            messages (List[dict]): List of messages in the conversation format

        Returns:
            str: Response content from the API, or empty string if all retries fail
        """

        def sync_call():
            """
            Synchronous function to make the actual API call with retry logic.
            """
            for attempt in range(self.max_retries + 1):
                try:
                    # Make the API call to DashScope Generation service
                    response = Generation.call(
                        model=self.model,
                        api_key=self.api_key,
                        messages=messages,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        result_format='message'
                    )

                    # Check if the API call was successful
                    if response.status_code == 200:
                        # Return the content of the first choice in the response
                        return response.output.choices[0].message.content
                    else:
                        # Log warning for failed API call
                        logger.warning(
                            f"Aliyun API call failed (attempt {attempt + 1}): {response.code} - {response.message}")
                        # Retry with exponential backoff if not the last attempt
                        if attempt < self.max_retries:
                            import time
                            time.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            logger.error(f"All retries failed for Aliyun API call.")
                            return ""  # Fallback to empty string
                except Exception as e:
                    # Log error for any exception during API call
                    logger.error(f"Exception during Aliyun API call: {e}")
                    # Retry with exponential backoff if not the last attempt
                    if attempt < self.max_retries:
                        import time
                        time.sleep(2 ** attempt)
                    else:
                        return ""
            return ""

        # Run the synchronous dashscope call in a thread pool to avoid blocking the asyncio event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_call)

    async def translate(self, text: str, target_lang: str) -> str:
        """
        Translate a single text segment to the target language.

        Args:
            text (str): Text to be translated
            target_lang (str): Target language for translation

        Returns:
            str: Translated text
        """
        # Load configuration for system prompt
        cfg = get_config()

        # System prompt that guides the LLM on LaTeX translation rules
        system_prompt = f"You are a professional LaTeX translator. Your task is to translate the following text from English to {target_lang}. CRITICAL RULES: 1. Preserve ALL LaTeX commands (e.g., \\section{{}}, \\cite{{}}, \\ref{{}}, \\begin{{equation}}, \\end{{equation}}, $...$, $$...$$) EXACTLY as they are. Do not translate the content inside {{}} of commands. 2. Do not translate mathematical formulas, variable names, or code snippets. 3. Maintain the original structure and formatting as much as possible. 4. Ensure the output is valid LaTeX that compiles correctly."

        # User prompt that provides the specific text to translate
        user_prompt = f"Translate the following source text to {target_lang}. Remember: Preserve LaTeX commands and structure!\n\nSource Text:\n{text}\n\nTranslated Text:"

        # Create the message format required by the API
        messages = [
            {"role": Role.SYSTEM, "content": system_prompt},  # System instruction
            {"role": Role.USER, "content": user_prompt}  # User request
        ]

        # Call the API and return the result
        return await self._call_api(messages)

    async def translate_batch(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate multiple text segments in batch mode.

        Args:
            texts (List[str]): List of texts to be translated
            target_lang (str): Target language for translation

        Returns:
            List[str]: List of translated texts
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
                logger.error(f"Error processing batch item {i} with Aliyun: {res}")
                processed_results.append(texts[i])  # Fallback to original
            else:
                # Add successful translation result
                processed_results.append(res)

        return processed_results