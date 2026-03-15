"""Unit tests for deep_browser_agent.providers."""


from deep_browser_agent.providers import (
    PROVIDER_PRESETS,
    ProviderConfig,
    get_provider_from_string,
)


class TestProviderConfig:
    def test_default_temperature(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet")
        assert pc.temperature == 0.0

    def test_default_api_key_none(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet")
        assert pc.api_key is None

    def test_default_base_url_none(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet")
        assert pc.base_url is None

    def test_default_api_version_none(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet")
        assert pc.api_version is None


class TestProviderConfigToKwargs:
    def test_anthropic_kwargs(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "anthropic:claude-3-5-sonnet"
        assert kwargs["temperature"] == 0.0

    def test_anthropic_explicit_api_key(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet", api_key="my-key")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "my-key"

    def test_openai_kwargs(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        pc = ProviderConfig(provider="openai", model="gpt-4o")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "openai:gpt-4o"
        assert kwargs["temperature"] == 0.0

    def test_openai_explicit_api_key(self):
        pc = ProviderConfig(provider="openai", model="gpt-4o", api_key="my-openai-key")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "my-openai-key"

    def test_openai_base_url(self):
        pc = ProviderConfig(provider="openai", model="gpt-4o", base_url="https://custom.openai.com")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["base_url"] == "https://custom.openai.com"

    def test_openai_no_base_url_omitted(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        pc = ProviderConfig(provider="openai", model="gpt-4o")
        kwargs = pc.to_init_chat_model_kwargs()
        assert "base_url" not in kwargs

    def test_openrouter_kwargs(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
        pc = ProviderConfig(provider="openrouter", model="deepseek/deepseek-chat-v3")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "openai:deepseek/deepseek-chat-v3"
        assert kwargs["base_url"] == "https://openrouter.ai/api/v1"

    def test_openrouter_explicit_api_key(self):
        pc = ProviderConfig(
            provider="openrouter", model="deepseek/deepseek-chat-v3", api_key="my-or-key"
        )
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "my-or-key"

    def test_openrouter_custom_base_url(self):
        pc = ProviderConfig(
            provider="openrouter", model="some/model", base_url="https://custom.router.com"
        )
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["base_url"] == "https://custom.router.com"

    def test_ollama_kwargs(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        pc = ProviderConfig(provider="ollama", model="llama3.3")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "ollama:llama3.3"
        assert kwargs["base_url"] == "http://localhost:11434"

    def test_ollama_custom_base_url(self):
        pc = ProviderConfig(provider="ollama", model="llama3.3", base_url="http://myserver:11434")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["base_url"] == "http://myserver:11434"

    def test_ollama_env_base_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://remote:11434")
        pc = ProviderConfig(provider="ollama", model="llama3.3")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["base_url"] == "http://remote:11434"

    def test_azure_kwargs(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://my.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
        pc = ProviderConfig(provider="azure", model="gpt-4o")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "azure-openai:gpt-4o"
        assert kwargs["api_version"] == "2024-12-01-preview"

    def test_azure_explicit_api_key(self):
        pc = ProviderConfig(provider="azure", model="gpt-4o", api_key="explicit-key")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "explicit-key"

    def test_azure_explicit_base_url(self):
        pc = ProviderConfig(
            provider="azure", model="gpt-4o", base_url="https://custom.azure.com"
        )
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["azure_endpoint"] == "https://custom.azure.com"

    def test_azure_explicit_api_version(self):
        pc = ProviderConfig(provider="azure", model="gpt-4o", api_version="2024-05-01-preview")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_version"] == "2024-05-01-preview"

    def test_google_kwargs(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        pc = ProviderConfig(provider="google", model="gemini-2.5-pro")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "google-genai:gemini-2.5-pro"

    def test_google_explicit_api_key(self):
        pc = ProviderConfig(provider="google", model="gemini-2.5-pro", api_key="my-google-key")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "my-google-key"

    def test_generic_provider_kwargs(self):
        pc = ProviderConfig(provider="groq", model="llama-3.3-70b")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["model"] == "groq:llama-3.3-70b"

    def test_generic_provider_with_api_key(self):
        pc = ProviderConfig(provider="groq", model="llama-3.3-70b", api_key="groq-key")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["api_key"] == "groq-key"

    def test_generic_provider_with_base_url(self):
        pc = ProviderConfig(provider="groq", model="llama-3.3-70b", base_url="https://api.groq.com")
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["base_url"] == "https://api.groq.com"

    def test_generic_provider_no_api_key_not_included(self):
        pc = ProviderConfig(provider="groq", model="llama-3.3-70b")
        kwargs = pc.to_init_chat_model_kwargs()
        assert "api_key" not in kwargs

    def test_temperature_preserved(self):
        pc = ProviderConfig(provider="anthropic", model="claude-3-5-sonnet", temperature=0.7)
        kwargs = pc.to_init_chat_model_kwargs()
        assert kwargs["temperature"] == 0.7


class TestProviderPresets:
    def test_presets_is_dict(self):
        assert isinstance(PROVIDER_PRESETS, dict)

    def test_anthropic_preset_exists(self):
        assert "anthropic" in PROVIDER_PRESETS

    def test_openai_preset_exists(self):
        assert "openai" in PROVIDER_PRESETS

    def test_azure_preset_exists(self):
        assert "azure" in PROVIDER_PRESETS

    def test_google_preset_exists(self):
        assert "google" in PROVIDER_PRESETS

    def test_each_preset_has_provider_and_model(self):
        for name, preset in PROVIDER_PRESETS.items():
            assert "provider" in preset, f"Preset '{name}' missing 'provider'"
            assert "model" in preset, f"Preset '{name}' missing 'model'"

    def test_anthropic_preset_values(self):
        assert PROVIDER_PRESETS["anthropic"]["provider"] == "anthropic"
        assert PROVIDER_PRESETS["anthropic"]["model"] == "claude-sonnet-4-20250514"

    def test_openai_preset_values(self):
        assert PROVIDER_PRESETS["openai"]["provider"] == "openai"
        assert PROVIDER_PRESETS["openai"]["model"] == "gpt-4o"


class TestGetProviderFromString:
    def test_preset_name_resolved(self):
        pc = get_provider_from_string("anthropic")
        assert pc.provider == "anthropic"
        assert pc.model == "claude-sonnet-4-20250514"

    def test_openai_preset_resolved(self):
        pc = get_provider_from_string("openai")
        assert pc.provider == "openai"
        assert pc.model == "gpt-4o"

    def test_provider_colon_model_format(self):
        pc = get_provider_from_string("anthropic:claude-3-5-sonnet")
        assert pc.provider == "anthropic"
        assert pc.model == "claude-3-5-sonnet"

    def test_openai_colon_model(self):
        pc = get_provider_from_string("openai:gpt-4o-mini")
        assert pc.provider == "openai"
        assert pc.model == "gpt-4o-mini"

    def test_ollama_colon_model(self):
        pc = get_provider_from_string("ollama:llama3.3")
        assert pc.provider == "ollama"
        assert pc.model == "llama3.3"

    def test_model_with_slash_in_name(self):
        pc = get_provider_from_string("openrouter:deepseek/deepseek-chat-v3")
        assert pc.provider == "openrouter"
        assert pc.model == "deepseek/deepseek-chat-v3"

    def test_model_only_defaults_to_anthropic(self):
        pc = get_provider_from_string("some-unknown-model")
        assert pc.provider == "anthropic"
        assert pc.model == "some-unknown-model"

    def test_returns_provider_config_instance(self):
        pc = get_provider_from_string("anthropic:claude-3-5-sonnet")
        assert isinstance(pc, ProviderConfig)

    def test_all_presets_return_provider_config(self):
        for preset_name in PROVIDER_PRESETS:
            pc = get_provider_from_string(preset_name)
            assert isinstance(pc, ProviderConfig)
            assert pc.provider
            assert pc.model

    def test_google_colon_model(self):
        pc = get_provider_from_string("google:gemini-2.5-flash")
        assert pc.provider == "google"
        assert pc.model == "gemini-2.5-flash"

    def test_azure_colon_model(self):
        pc = get_provider_from_string("azure:gpt-4o")
        assert pc.provider == "azure"
        assert pc.model == "gpt-4o"
