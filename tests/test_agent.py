"""Unit tests for deep_browser_agent.agent."""


from deep_browser_agent.agent import DEFAULT_SYSTEM_PROMPT, BrowserAgentSession
from deep_browser_agent.config import AgentConfig


class TestDefaultSystemPrompt:
    def test_is_string(self):
        assert isinstance(DEFAULT_SYSTEM_PROMPT, str)

    def test_is_not_empty(self):
        assert len(DEFAULT_SYSTEM_PROMPT) > 100

    def test_mentions_uid(self):
        assert "uid" in DEFAULT_SYSTEM_PROMPT.lower() or "UID" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_take_snapshot(self):
        assert "take_snapshot" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_navigate_page(self):
        assert "navigate_page" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_fill(self):
        assert "fill" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_click(self):
        assert "click" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_evaluate_script(self):
        assert "evaluate_script" in DEFAULT_SYSTEM_PROMPT

    def test_mentions_take_screenshot(self):
        assert "take_screenshot" in DEFAULT_SYSTEM_PROMPT


class TestBrowserAgentSessionInit:
    def test_default_init(self):
        session = BrowserAgentSession()
        assert session._config is None
        assert session._extra_tools is None
        assert session._agent is None
        assert session._client is None

    def test_init_with_config(self):
        config = AgentConfig(model="anthropic:claude-3-5-sonnet", headless=True)
        session = BrowserAgentSession(config=config)
        assert session._config is config

    def test_init_with_extra_tools(self):
        session = BrowserAgentSession(extra_tools=["fake_tool"])
        assert session._extra_tools == ["fake_tool"]

    def test_agent_property_none_before_enter(self):
        session = BrowserAgentSession()
        assert session.agent is None

    def test_agent_property_returns_agent(self):
        session = BrowserAgentSession()
        sentinel_agent = object()
        session._agent = sentinel_agent
        assert session.agent is sentinel_agent
