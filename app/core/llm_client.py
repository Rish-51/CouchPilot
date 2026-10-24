"""Gemma LLM client using OpenAI-compatible SDK with Sentry tracing and token accounting."""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.models import Patch, Target
from app.core.sentry_ops import get_sentry_manager


class TargetDocumentationResult(BaseModel):
    qualified_name: str
    docstring: str = Field(description="Clean, concise Google-style docstring")
    param_annotations: Dict[str, str] = Field(default_factory=dict, description="Parameter type annotations")
    return_annotation: Optional[str] = Field(default=None, description="Return type annotation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FileBatchDocumentation(BaseModel):
    results: List[TargetDocumentationResult]


class GemmaClient:
    """Client for open-weight Gemma models via Groq, Google AI Studio, or Ollama."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        fallback_model_id: Optional[str] = None
    ) -> None:
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "dummy-key")
        self.model_id = model_id or os.getenv("LLM_MODEL_ID", "gemma2-9b-it")
        self.fallback_model_id = fallback_model_id or os.getenv("LLM_FALLBACK_MODEL_ID", "gemma-2-9b-it")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=45.0,
        )
        self.sentry = get_sentry_manager()

    def verify_model(self) -> str:
        """Verify configured model ID is served by endpoint, otherwise fallback."""
        try:
            models_page = self.client.models.list()
            available = {m.id for m in models_page.data}
            if self.model_id in available:
                return self.model_id
            if self.fallback_model_id in available:
                self.model_id = self.fallback_model_id
                return self.model_id
        except Exception:
            pass
        return self.model_id

    def generate_batch(
        self,
        file_path: str,
        file_content: str,
        targets: List[Target]
    ) -> Tuple[List[Patch], int, int, int]:
        """Generate docstrings and type annotations for a batch of targets."""
        if not targets:
            return [], 0, 0, 0

        target_prompts = []
        for t in targets:
            target_prompts.append({
                "qualified_name": t.qualified_name,
                "type": t.target_type.value,
                "signature": t.signature,
                "missing_docstring": t.missing_docstring,
                "missing_parameters": t.missing_type_annotations,
                "needs_return_annotation": not t.has_return_annotation,
            })

        system_prompt = (
            "You are an expert Python static analysis documentation agent. "
            "Generate concise, accurate Google-style docstrings and valid Python 3 type annotations "
            "for the requested functions/classes. "
            "Never alter or output business logic code. "
            "Return strictly valid JSON adhering to this schema:\n"
            "{\n"
            '  "results": [\n'
            '    {\n'
            '      "qualified_name": "str",\n'
            '      "docstring": "str",\n'
            '      "param_annotations": {"param": "type"},\n'
            '      "return_annotation": "type",\n'
            '      "confidence": 0.95\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        user_prompt = (
            f"File: {file_path}\n"
            f"Source Context Snippet:\n{file_content[:1500]}\n\n"
            f"Targets requiring documentation:\n{json.dumps(target_prompts, indent=2)}\n\n"
            "Provide the documentation JSON now:"
        )

        max_retries = 3
        retry_count = 0
        tokens_in = 0
        tokens_out = 0
        start_time = time.time()

        while retry_count < max_retries:
            with self.sentry.span(
                op="llm.generate",
                description=f"Generate documentation batch for {len(targets)} targets",
                tags={"model": self.model_id, "provider": self.base_url},
                data={"batch_size": len(targets), "retry": retry_count}
            ) as span:
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.1,
                        max_tokens=1500,
                        response_format={"type": "json_object"},
                    )

                    usage = response.usage
                    if usage:
                        tokens_in += usage.prompt_tokens
                        tokens_out += usage.completion_tokens

                    raw_content = response.choices[0].message.content or "{}"
                    clean_json = self._extract_json(raw_content)
                    batch_data = FileBatchDocumentation.model_validate_json(clean_json)

                    latency_ms = int((time.time() - start_time) * 1000)
                    if span:
                        span.set_data("tokens_in", tokens_in)
                        span.set_data("tokens_out", tokens_out)
                        span.set_data("latency_ms", latency_ms)
                        span.set_data("retries", retry_count)

                    # Build Patch objects
                    patches: List[Patch] = []
                    target_map = {t.qualified_name: t for t in targets}
                    for res in batch_data.results:
                        if res.qualified_name in target_map:
                            t = target_map[res.qualified_name]
                            patches.append(
                                Patch(
                                    target_qualified_name=t.qualified_name,
                                    file_path=t.file_path,
                                    start_byte=t.start_byte,
                                    end_byte=t.end_byte,
                                    generated_docstring=res.docstring,
                                    param_annotations=res.param_annotations,
                                    return_annotation=res.return_annotation,
                                    confidence=res.confidence,
                                )
                            )

                    return patches, tokens_in, tokens_out, latency_ms

                except Exception as e:
                    retry_count += 1
                    time.sleep(1.0 * retry_count)
                    if retry_count >= max_retries:
                        latency_ms = int((time.time() - start_time) * 1000)
                        return [], tokens_in, tokens_out, latency_ms

        latency_ms = int((time.time() - start_time) * 1000)
        return [], tokens_in, tokens_out, latency_ms

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON block from text, stripping any markdown backticks."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
