"""Unit tests for deep_browser_agent.config."""


from deep_browser_agent.config import AgentConfig


class TestAgentConfigDefaults:
    def test_default_model(self):
        config = AgentConfig()
        assert config.model == "anthropic:claude-sonnet-4-20250514"

    def test_default_temperature(self):
        config = AgentConfig()
        assert config.temperature == 0.0

    def test_default_headless(self):
        config = AgentConfig()
        assert config.headless is False

    def test_default_slim_mode(self):
        config = AgentConfig()
        assert config.slim_mode is False

    def test_default_isolated(self):
        config = AgentConfig()
        assert config.isolated is True

    def test_default_viewport(self):
        config = AgentConfig()
        assert config.viewport == "1920x1080"

    def test_default_max_iterations(self):
        config = AgentConfig()
        assert config.max_iterations == 50

    def test_default_no_usage_stats(self):
        config = AgentConfig()
        assert config.no_usage_stats is True

    def test_default_api_key_is_none(self):
        config = AgentConfig()
        assert config.api_key is None

    def test_default_base_url_is_none(self):
        config = AgentConfig()
        assert config.base_url is None

    def test_default_browser_url_is_none(self):
        config = AgentConfig()
        assert config.browser_url is None

    def test_default_chrome_channel_is_none(self):
        config = AgentConfig()
        assert config.chrome_channel is None

    def test_default_system_prompt_is_none(self):
        config = AgentConfig()
        assert config.system_prompt is None


class TestAgentConfigGetMcpArgs:
    def test_base_args_always_present(self):
        config = AgentConfig()
        args = config.get_mcp_args()
        assert "-y" in args
        assert "chrome-devtools-mcp@latest" in args

    def test_headless_flag_added_when_true(self):
        config = AgentConfig(headless=True)
        args = config.get_mcp_args()
        assert "--headless" in args

    def test_headless_flag_absent_when_false(self):
        config = AgentConfig(headless=False)
        args = config.get_mcp_args()
        assert "--headless" not in args

    def test_slim_flag_added_when_true(self):
        config = AgentConfig(slim_mode=True)
        args = config.get_mcp_args()
        assert "--slim" in args

    def test_slim_flag_absent_when_false(self):
        config = AgentConfig(slim_mode=False)
        args = config.get_mcp_args()
        assert "--slim" not in args

    def test_isolated_flag_added_when_true(self):
        config = AgentConfig(isolated=True)
        args = config.get_mcp_args()
        assert "--isolated" in args

    def test_isolated_flag_absent_when_false(self):
        config = AgentConfig(isolated=False)
        args = config.get_mcp_args()
        assert "--isolated" not in args

    def test_no_usage_statistics_flag_added_when_true(self):
        config = AgentConfig(no_usage_stats=True)
        args = config.get_mcp_args()
        assert "--no-usage-statistics" in args

    def test_no_usage_statistics_absent_when_false(self):
        config = AgentConfig(no_usage_stats=False)
        args = config.get_mcp_args()
        assert "--no-usage-statistics" not in args

    def test_viewport_added(self):
        config = AgentConfig(viewport="1280x720")
        args = config.get_mcp_args()
        assert "--viewport" in args
        assert "1280x720" in args

    def test_viewport_position_correct(self):
        config = AgentConfig(viewport="800x600")
        args = config.get_mcp_args()
        idx = args.index("--viewport")
        assert args[idx + 1] == "800x600"

    def test_browser_url_added(self):
        config = AgentConfig(browser_url="http://localhost:9222")
        args = config.get_mcp_args()
        assert "--browserUrl" in args
        assert "http://localhost:9222" in args

    def test_browser_url_position_correct(self):
        config = AgentConfig(browser_url="http://localhost:9222")
        args = config.get_mcp_args()
        idx = args.index("--browserUrl")
        assert args[idx + 1] == "http://localhost:9222"

    def test_browser_url_absent_when_none(self):
        config = AgentConfig(browser_url=None)
        args = config.get_mcp_args()
        assert "--browserUrl" not in args

    def test_chrome_channel_added(self):
        config = AgentConfig(chrome_channel="canary")
        args = config.get_mcp_args()
        assert "--channel" in args
        assert "canary" in args

    def test_chrome_channel_position_correct(self):
        config = AgentConfig(chrome_channel="beta")
        args = config.get_mcp_args()
        idx = args.index("--channel")
        assert args[idx + 1] == "beta"

    def test_chrome_channel_absent_when_none(self):
        config = AgentConfig(chrome_channel=None)
        args = config.get_mcp_args()
        assert "--channel" not in args

    def test_all_flags_together(self):
        config = AgentConfig(
            headless=True,
            slim_mode=True,
            isolated=True,
            no_usage_stats=True,
            viewport="1920x1080",
            browser_url="http://localhost:9222",
            chrome_channel="stable",
        )
        args = config.get_mcp_args()
        assert "--headless" in args
        assert "--slim" in args
        assert "--isolated" in args
        assert "--no-usage-statistics" in args
        assert "--viewport" in args
        assert "1920x1080" in args
        assert "--browserUrl" in args
        assert "http://localhost:9222" in args
        assert "--channel" in args
        assert "stable" in args

    def test_returns_new_list_each_call(self):
        config = AgentConfig()
        args1 = config.get_mcp_args()
        args2 = config.get_mcp_args()
        assert args1 == args2
        assert args1 is not args2


class TestAgentConfigFromEnv:
    def test_from_env_defaults(self, monkeypatch):
        """from_env() uses sensible defaults when no env vars are set."""
        for var in [
            "AGENT_MODEL", "AGENT_MODEL_PROVIDER", "AGENT_MODEL_NAME",
            "AGENT_API_KEY", "AGENT_BASE_URL",
            "CHROME_HEADLESS", "CHROME_SLIM", "CHROME_ISOLATED",
            "CHROME_BROWSER_URL", "CHROME_CHANNEL", "CHROME_VIEWPORT",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = AgentConfig.from_env()
        assert config.model == "anthropic:claude-sonnet-4-20250514"
        assert config.headless is False
        assert config.isolated is True
        assert config.viewport == "1920x1080"

    def test_from_env_model_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_MODEL", "openai:gpt-4o")
        config = AgentConfig.from_env()
        assert config.model == "openai:gpt-4o"

    def test_from_env_provider_and_name(self, monkeypatch):
        monkeypatch.delenv("AGENT_MODEL", raising=False)
        monkeypatch.setenv("AGENT_MODEL_PROVIDER", "openai")
        monkeypatch.setenv("AGENT_MODEL_NAME", "gpt-4o-mini")
        config = AgentConfig.from_env()
        assert config.model == "openai:gpt-4o-mini"

    def test_from_env_headless_true(self, monkeypatch):
        monkeypatch.setenv("CHROME_HEADLESS", "true")
        config = AgentConfig.from_env()
        assert config.headless is True

    def test_from_env_headless_false(self, monkeypatch):
        monkeypatch.setenv("CHROME_HEADLESS", "false")
        config = AgentConfig.from_env()
        assert config.headless is False

    def test_from_env_isolated_false(self, monkeypatch):
        monkeypatch.setenv("CHROME_ISOLATED", "false")
        config = AgentConfig.from_env()
        assert config.isolated is False

    def test_from_env_viewport(self, monkeypatch):
        monkeypatch.setenv("CHROME_VIEWPORT", "1280x720")
        config = AgentConfig.from_env()
        assert config.viewport == "1280x720"

    def test_from_env_browser_url(self, monkeypatch):
        monkeypatch.setenv("CHROME_BROWSER_URL", "http://localhost:9222")
        config = AgentConfig.from_env()
        assert config.browser_url == "http://localhost:9222"

    def test_from_env_api_key(self, monkeypatch):
        monkeypatch.setenv("AGENT_API_KEY", "sk-test-123")
        config = AgentConfig.from_env()
        assert config.api_key == "sk-test-123"

    def test_from_env_base_url(self, monkeypatch):
        monkeypatch.setenv("AGENT_BASE_URL", "https://api.example.com")
        config = AgentConfig.from_env()
        assert config.base_url == "https://api.example.com"

    def test_from_env_slim_mode(self, monkeypatch):
        monkeypatch.setenv("CHROME_SLIM", "true")
        config = AgentConfig.from_env()
        assert config.slim_mode is True

    def test_from_env_chrome_channel(self, monkeypatch):
        monkeypatch.setenv("CHROME_CHANNEL", "canary")
        config = AgentConfig.from_env()
        assert config.chrome_channel == "canary"
