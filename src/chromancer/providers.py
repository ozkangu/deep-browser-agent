"""Multi-provider LLM support: Anthropic, OpenAI, OpenRouter, Ollama, Azure AI Foundry, Google."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """LLM provider configuration."""

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    api_version: str | None = None
    temperature: float = 0.0

    def to_init_chat_model_kwargs(self) -> dict:
        """Convert to kwargs for langchain's init_chat_model."""
        kwargs: dict = {"temperature": self.temperature}

        if self.provider == "openrouter":
            kwargs["model"] = f"openai:{self.model}"
            kwargs["api_key"] = self.api_key or os.getenv("OPENROUTER_API_KEY")
            kwargs["base_url"] = self.base_url or "https://openrouter.ai/api/v1"

        elif self.provider == "ollama":
            kwargs["model"] = f"ollama:{self.model}"
            kwargs["base_url"] = self.base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        elif self.provider == "azure":
            kwargs["model"] = f"azure-openai:{self.model}"
            kwargs["api_key"] = self.api_key or os.getenv("AZURE_OPENAI_API_KEY")
            kwargs["azure_endpoint"] = self.base_url or os.getenv("AZURE_OPENAI_ENDPOINT")
            kwargs["api_version"] = self.api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        elif self.provider == "google":
            kwargs["model"] = f"google-genai:{self.model}"
            kwargs["api_key"] = self.api_key or os.getenv("GOOGLE_API_KEY")

        elif self.provider == "openai":
            kwargs["model"] = f"openai:{self.model}"
            kwargs["api_key"] = self.api_key or os.getenv("OPENAI_API_KEY")
            if self.base_url:
                kwargs["base_url"] = self.base_url

        elif self.provider == "anthropic":
            kwargs["model"] = f"anthropic:{self.model}"
            kwargs["api_key"] = self.api_key or os.getenv("ANTHROPIC_API_KEY")

        else:
            # Generic: pass provider:model directly (e.g., "groq:llama-3.3-70b")
            kwargs["model"] = f"{self.provider}:{self.model}"
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url

        return kwargs


def create_model(provider_config: ProviderConfig):
    """Create a LangChain chat model from provider config."""
    from langchain.chat_models import init_chat_model

    kwargs = provider_config.to_init_chat_model_kwargs()
    model_str = kwargs.pop("model")
    return init_chat_model(model_str, **kwargs)


# --- Presets for quick setup ---

PROVIDER_PRESETS: dict[str, dict] = {
    "anthropic": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "openai": {"provider": "openai", "model": "gpt-4o"},
    "openrouter-claude": {"provider": "openrouter", "model": "anthropic/claude-sonnet-4-20250514"},
    "openrouter-gpt4o": {"provider": "openrouter", "model": "openai/gpt-4o"},
    "openrouter-deepseek": {"provider": "openrouter", "model": "deepseek/deepseek-chat-v3"},
    "openrouter-llama": {"provider": "openrouter", "model": "meta-llama/llama-4-maverick"},
    "ollama-llama": {"provider": "ollama", "model": "llama3.3"},
    "ollama-qwen": {"provider": "ollama", "model": "qwen2.5:32b"},
    "azure": {"provider": "azure", "model": "gpt-4o"},
    "google": {"provider": "google", "model": "gemini-2.5-pro"},
}


def get_provider_from_string(provider_model: str) -> ProviderConfig:
    """Parse 'provider:model' string or preset name into ProviderConfig.

    Examples:
        "anthropic:claude-sonnet-4-20250514"
        "openrouter:anthropic/claude-sonnet-4-20250514"
        "ollama:llama3.3"
        "azure:gpt-4o"
        "openrouter-claude"  (preset)
    """
    # Check presets first
    if provider_model in PROVIDER_PRESETS:
        return ProviderConfig(**PROVIDER_PRESETS[provider_model])

    if ":" in provider_model:
        provider, model = provider_model.split(":", 1)
        return ProviderConfig(provider=provider, model=model)

    # Default: treat as anthropic model name
    return ProviderConfig(provider="anthropic", model=provider_model)
