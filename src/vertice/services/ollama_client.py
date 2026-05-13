import logging
from time import perf_counter

import requests


class OllamaConfigurationError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int, error_logger=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.error_logger = error_logger
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, context: dict | None = None) -> str:
        started_at = perf_counter()
        self.logger.info(
            "[OLLAMA] request started | model=%s | prompt_chars=%s | base_url=%s",
            self.model,
            len(prompt),
            self.base_url,
        )
        endpoint_attempts: list[dict] = []

        try:
            for endpoint_name, endpoint_path, payload, parser in self._request_strategies(prompt):
                response = requests.post(
                    f"{self.base_url}{endpoint_path}",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                attempt = {
                    "endpoint_name": endpoint_name,
                    "endpoint_path": endpoint_path,
                    "status_code": response.status_code,
                    "response_preview": response.text[:300],
                }
                endpoint_attempts.append(attempt)

                if response.status_code in {404, 405}:
                    self.logger.warning(
                        "[OLLAMA] endpoint unavailable | model=%s | endpoint=%s | status=%s",
                        self.model,
                        endpoint_path,
                        response.status_code,
                    )
                    continue

                response.raise_for_status()
                payload = response.json()
                generated_text = parser(payload).strip()
                if not generated_text:
                    raise ValueError(
                        f"A resposta do endpoint {endpoint_path} nao trouxe texto gerado."
                    )

                elapsed_seconds = perf_counter() - started_at
                self.logger.info(
                    "[OLLAMA] request finished | model=%s | endpoint=%s | response_chars=%s | elapsed=%.2fs",
                    self.model,
                    endpoint_path,
                    len(generated_text),
                    elapsed_seconds,
                )
                return generated_text

            raise OllamaConfigurationError(
                "Nenhum endpoint compativel com Ollama respondeu corretamente. "
                "Verifique se a URL base aponta para o servidor certo e se ele expoe "
                "/api/generate, /api/chat ou /v1/chat/completions."
            )
        except Exception as exc:
            elapsed_seconds = perf_counter() - started_at
            if self.error_logger is not None:
                self.error_logger.log_error(
                    operation="ollama_generate",
                    stage="request",
                    error=exc,
                    context={
                        **(context or {}),
                        "model": self.model,
                        "base_url": self.base_url,
                        "timeout_seconds": self.timeout_seconds,
                        "prompt_chars": len(prompt),
                        "prompt_preview": prompt[:500],
                        "elapsed_seconds": round(elapsed_seconds, 2),
                        "endpoint_attempts": endpoint_attempts,
                    },
                )
            self.logger.exception(
                "[OLLAMA] request failed | model=%s | elapsed=%.2fs | message=%s",
                self.model,
                elapsed_seconds,
                exc,
            )
            raise

    def _request_strategies(self, prompt: str) -> list[tuple[str, str, dict, object]]:
        return [
            (
                "ollama_generate",
                "/api/generate",
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                self._parse_generate_response,
            ),
            (
                "ollama_chat",
                "/api/chat",
                {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "stream": False,
                },
                self._parse_chat_response,
            ),
            (
                "openai_compatible_chat",
                "/v1/chat/completions",
                {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                },
                self._parse_openai_chat_response,
            ),
        ]

    def _parse_generate_response(self, payload: dict) -> str:
        return str(payload.get("response", ""))

    def _parse_chat_response(self, payload: dict) -> str:
        message = payload.get("message") or {}
        return str(message.get("content", ""))

    def _parse_openai_chat_response(self, payload: dict) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content", ""))
