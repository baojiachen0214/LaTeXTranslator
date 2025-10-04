import asyncio
import unicodedata
import re
from typing import List
from trans.config import get_config
from trans.llm.factory import get_llm
from trans.core.placeholder import PlaceholderManager, PROTECTED_PATTERNS
from trans.core.chunker import ContextAwareChunker
from trans.utils.logger import logger
from trans.utils.helpers import fix_command_adhesion, fix_hyphen_spacing, remove_llm_artifacts, fix_llm_latex_artifacts

# Regular expression pattern to match CJK (Chinese, Japanese, Korean) characters
# Unicode range \u4e00-\u9fff covers the main CJK unified ideographs
CJK_RE = re.compile(r'[\u4e00-\u9fff]')


class TexTranslator:
    """
    A LaTeX document translator that handles complex LaTeX structures while preserving
    formatting, equations, and other protected content during translation.

    This class uses placeholder management to protect sensitive LaTeX content,
    context-aware chunking for optimal translation boundaries, and post-processing
    to fix common translation artifacts.
    """

    def __init__(self):
        """
        Initialize the TexTranslator with configuration, LLM, and chunker.
        """
        # Load configuration from the system
        self.config = get_config()
        # Initialize the Large Language Model for translation
        self.llm = get_llm()
        # Initialize context-aware chunker with configured chunk size
        self.chunker = ContextAwareChunker(self.config.translation.chunk_size)

    async def translate_content(self, content: str) -> str:
        """
        Translate LaTeX content while preserving structure and protected elements.

        Args:
            content (str): Original LaTeX content to be translated

        Returns:
            str: Translated LaTeX content with original structure preserved
        """
        # Initialize placeholder manager to protect sensitive content
        pm = PlaceholderManager()

        # Replace protected patterns (equations, citations, etc.) with placeholders
        protected_content = pm.replace_in_text(content, PROTECTED_PATTERNS)

        # Split the protected content into manageable chunks for translation
        chunks = self.chunker.split(protected_content)
        logger.info(f"Split content into {len(chunks)} chunks for translation.")

        # Perform batch translation of all chunks
        translated_chunks = await self.llm.translate_batch(chunks, self.config.translation.target_lang)

        # If translate_batch returns exception items that have been fallen back to original chunks,
        # we need to detect and retry them
        # Detect "untranslated" or "fallen back to original" chunks (strict comparison after stripping)
        max_retries = getattr(self.config.translation, "max_retries_per_chunk", 2)

        # Process any chunks that raised exceptions during batch translation
        for idx, (orig_chunk, trans_chunk) in enumerate(zip(chunks, translated_chunks)):
            if isinstance(trans_chunk, Exception):
                logger.warning(f"Chunk {idx} raised exception during batch translate; will attempt retry.")
                translated_chunks[idx] = orig_chunk  # fallback for now

        # First-pass detection of identical chunks (likely untranslated)
        untranslated_indices: List[int] = []
        for idx, (orig_chunk, trans_chunk) in enumerate(zip(chunks, translated_chunks)):
            # Check if translation is None or if original and translated chunks are identical after stripping
            if (trans_chunk is None) or (orig_chunk.strip() == trans_chunk.strip()):
                untranslated_indices.append(idx)

        # Try to retranslate those untranslated chunks individually (stronger single-call retry)
        for idx in untranslated_indices.copy():
            success = False
            for attempt in range(max_retries):
                try:
                    logger.info(f"Retrying translation for chunk {idx} (attempt {attempt + 1}/{max_retries})")
                    # Attempt single-chunk translation with retry
                    single_trans = await self.llm.translate(chunks[idx], self.config.translation.target_lang)
                    # Check if translation was successful (not identical to original after stripping)
                    if single_trans and single_trans.strip() != chunks[idx].strip():
                        translated_chunks[idx] = single_trans
                        success = True
                        break
                except Exception as e:
                    logger.warning(f"Single-chunk translate exception for chunk {idx}: {e}")

            if not success:
                logger.error(f"Chunk {idx} appears untranslated after retries; marking for manual review.")
                # Leave in untranslated_indices for logging/review (don't automatically write back original)
            else:
                # Remove successfully translated chunk from untranslated list
                untranslated_indices.remove(idx)

        # If there are still remaining untranslated chunks, log detailed information (with context snippets for manual review)
        if untranslated_indices:
            for idx in untranslated_indices:
                # Create a snippet of the first 200 characters, replacing newlines with \n for logging
                snippet = chunks[idx][:200].replace('\n', '\\n')
                logger.warning(f"Untranslated chunk index {idx} (snippet): {snippet}")

        # Reassemble the translated protected text by joining all translated chunks
        translated_protected = "".join(translated_chunks)

        # Restore the original protected content by replacing placeholders with original content
        restored_content = pm.restore(translated_protected)

        # Post-process the content to fix common translation artifacts
        if self.config.translation.fix_hyphen:
            # Fix spacing around hyphens that may have been affected by translation
            restored_content = fix_hyphen_spacing(restored_content)
        if self.config.translation.fix_command_adhesion:
            # Fix issues where LaTeX commands may have become improperly attached
            restored_content = fix_command_adhesion(restored_content)

        # Basic artifact removal based on comparison with original content
        restored_content = remove_llm_artifacts(restored_content, content)

        # Apply powerful fix for common LLM LaTeX artifacts
        restored_content = fix_llm_latex_artifacts(restored_content, content)

        # Normalize Unicode and ensure UTF-8 safe characters (NFC normalization)
        # This helps ensure consistent character representation
        restored_content = unicodedata.normalize('NFC', restored_content)

        # Quick sanity check: if original had CJK characters and restored has none, try whole-doc retry
        # This catches cases where translation failed to preserve language-specific characters
        original_has_cjk = bool(CJK_RE.search(content))
        restored_has_cjk = bool(CJK_RE.search(restored_content))

        if original_has_cjk and not restored_has_cjk:
            logger.error("Original document contains CJK characters but translated result contains none. "
                         "Attempting one full-document retranslation as fallback.")
            try:
                # Attempt full document translation as a fallback
                full_retry = await self.llm.translate(content, self.config.translation.target_lang)

                if full_retry and full_retry.strip() != content.strip():
                    # Repeat the same restore/postprocess flow for the full retry
                    protected_retry = pm.replace_in_text(full_retry, PROTECTED_PATTERNS)
                    # Best effort: skip chunker here and restore placeholders directly
                    restored_retry = pm.restore(protected_retry)

                    # Apply same post-processing steps to the retry result
                    if self.config.translation.fix_hyphen:
                        restored_retry = fix_hyphen_spacing(restored_retry)
                    if self.config.translation.fix_command_adhesion:
                        restored_retry = fix_command_adhesion(restored_retry)
                    restored_retry = remove_llm_artifacts(restored_retry, content)
                    restored_retry = fix_llm_latex_artifacts(restored_retry, content)
                    restored_retry = unicodedata.normalize('NFC', restored_retry)

                    # Check if the retry successfully restored CJK characters
                    if CJK_RE.search(restored_retry):
                        logger.info("Full-document retry appears to restore CJK characters.")
                        restored_content = restored_retry
                    else:
                        logger.error(
                            "Full-document retry did not restore CJK; leaving previous result and flagging for manual review.")
                else:
                    logger.error("Full-document retry returned no useful translation; leaving previous result.")
            except Exception as e:
                logger.error(f"Exception during full-document retry: {e}")

        return restored_content