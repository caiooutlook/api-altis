"""
Módulo de abstração do LLM - suporta OpenAI e Anthropic.

Permite trocar entre providers via configuração sem alterar o código dos agentes.
"""

from openai import OpenAI
from anthropic import Anthropic

from src.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
)


class LLMClient:
    """Cliente unificado para chamadas ao LLM (OpenAI ou Anthropic)."""

    def __init__(self, provider: str = None):
        self.provider = provider or LLM_PROVIDER

        if self.provider == "openai":
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = OPENAI_MODEL
        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self.model = ANTHROPIC_MODEL
        else:
            raise ValueError(f"Provider não suportado: {self.provider}. Use 'openai' ou 'anthropic'.")

    def complete(self, prompt: str, system: str = None, temperature: float = 0.1, max_tokens: int = 2000) -> str:
        """
        Gera uma resposta a partir de um prompt.

        Args:
            prompt: Mensagem do usuário / prompt principal
            system: System prompt (opcional)
            temperature: Criatividade (0.0 = determinístico)
            max_tokens: Limite de tokens na resposta

        Returns:
            Texto da resposta
        """
        if self.provider == "openai":
            return self._complete_openai(prompt, system, temperature, max_tokens)
        else:
            return self._complete_anthropic(prompt, system, temperature, max_tokens)

    def _complete_openai(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _complete_anthropic(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text.strip()

    def get_model_info(self) -> str:
        """Retorna info do modelo em uso."""
        return f"{self.provider}/{self.model}"
