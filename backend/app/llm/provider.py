import os
import logging
import hashlib
from typing import List, Dict, Optional, Any
from app.core.config import settings

logger = logging.getLogger("greppa.llm")

class LLMProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    def is_configured(self) -> bool:
        return self._client is not None

    def generate_summary(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Generates a concise code/file/folder summary using the cheap/fast model (e.g. gemini-2.0-flash).
        Falls back to structural heuristic summary if no API key is provided.
        """
        model_name = model or settings.CHEAP_MODEL_NAME
        if self._client:
            try:
                contents = prompt
                if system_prompt:
                    contents = f"{system_prompt}\n\n{prompt}"
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini generate_summary error: {e}. Falling back to heuristic summary.")

        # Heuristic fallback summary if Gemini API key not provided or quota exceeded
        return self._heuristic_summary(prompt)

    def generate_answer(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generates an architectural answer or agent reasoning step using the strong model (e.g. gemini-2.0-pro).
        """
        model_name = model or settings.STRONG_MODEL_NAME
        if self._client:
            try:
                contents = prompt
                if system_instruction:
                    contents = f"{system_instruction}\n\n{prompt}"
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini generate_answer error: {e}. Falling back to heuristic synthesis.")

        return (
            "### Greppa Retrieval Synthesis\n\n"
            "Based on the retrieved symbols and call graph context:\n"
            + prompt[:1200]
            + "\n\n*(Note: Provide a Gemini API Key to enable full deep generative synthesis)*"
        )

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings (dim: 768) for a batch of texts.
        Uses Gemini text-embedding-004 when key is present, or deterministic pseudo-embeddings for tests.
        """
        if not texts:
            return []

        if self._client:
            try:
                embeddings = []
                for text in texts:
                    res = self._client.models.embed_content(
                        model=settings.EMBEDDING_MODEL_NAME,
                        contents=text[:2048]
                    )
                    if hasattr(res, 'embedding') and hasattr(res.embedding, 'values'):
                        embeddings.append(list(res.embedding.values))
                    elif hasattr(res, 'embeddings') and len(res.embeddings) > 0:
                        embeddings.append(list(res.embeddings[0].values))
                    else:
                        embeddings.append(self._pseudo_embedding(text, settings.EMBEDDING_DIM))
                return embeddings
            except Exception as e:
                logger.warning(f"Gemini embed_content error: {e}. Falling back to deterministic embeddings.")

        return [self._pseudo_embedding(t, settings.EMBEDDING_DIM) for t in texts]

    def _pseudo_embedding(self, text: str, dim: int = 768) -> List[float]:
        """
        Generates a normalized deterministic dense vector from text for offline tests.
        Preserves keyword token frequency so similarity ranking works offline.
        """
        import numpy as np
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h // dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec.tolist()

    def _heuristic_summary(self, prompt: str) -> str:
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        first_few = [l for l in lines if not l.startswith("```") and len(l) > 5][:4]
        return f"Component summary: {' | '.join(first_few)}" if first_few else "Module component definition."

def get_llm_provider(api_key: Optional[str] = None) -> LLMProvider:
    return LLMProvider(api_key=api_key)
