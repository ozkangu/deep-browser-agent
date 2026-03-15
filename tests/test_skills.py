"""Unit tests for deep_browser_agent.skills."""


from deep_browser_agent.skills import (
    debug_page,
    extract_data_js,
    form_fill_guide,
    get_browser_skills,
    handle_bot_detection,
    multi_tab_workflow,
    performance_audit_guide,
    snapshot_and_plan,
)


class TestGetBrowserSkills:
    def test_returns_list(self):
        skills = get_browser_skills()
        assert isinstance(skills, list)

    def test_returns_seven_skills(self):
        skills = get_browser_skills()
        assert len(skills) == 7

    def test_all_skills_have_invoke(self):
        for skill in get_browser_skills():
            assert hasattr(skill, "invoke")

    def test_skill_names(self):
        skills = get_browser_skills()
        names = [s.name for s in skills]
        assert "snapshot_and_plan" in names
        assert "extract_data_js" in names
        assert "form_fill_guide" in names
        assert "handle_bot_detection" in names
        assert "debug_page" in names
        assert "multi_tab_workflow" in names
        assert "performance_audit_guide" in names


class TestSnapshotAndPlan:
    def test_output_contains_goal(self):
        result = snapshot_and_plan.invoke({"goal": "log in to the site"})
        assert "log in to the site" in result

    def test_output_contains_workflow_steps(self):
        result = snapshot_and_plan.invoke({"goal": "test"})
        assert "take_snapshot" in result
        assert "uid" in result.lower()

    def test_output_mentions_uid(self):
        result = snapshot_and_plan.invoke({"goal": "click a button"})
        assert "uid" in result.lower()

    def test_output_is_string(self):
        result = snapshot_and_plan.invoke({"goal": "anything"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestExtractDataJs:
    def test_title_keyword_matches(self):
        result = extract_data_js.invoke({"description": "page title"})
        assert "document.title" in result

    def test_links_keyword_matches(self):
        result = extract_data_js.invoke({"description": "all links on the page"})
        assert "querySelectorAll" in result

    def test_headings_keyword_matches(self):
        result = extract_data_js.invoke({"description": "headings"})
        assert "h1" in result or "h2" in result

    def test_images_keyword_matches(self):
        result = extract_data_js.invoke({"description": "images"})
        assert "img" in result

    def test_tables_keyword_matches(self):
        result = extract_data_js.invoke({"description": "tables"})
        assert "table" in result

    def test_text_keyword_matches(self):
        result = extract_data_js.invoke({"description": "body text content"})
        assert "innerText" in result or "body" in result

    def test_forms_keyword_matches(self):
        result = extract_data_js.invoke({"description": "forms and inputs"})
        assert "input" in result

    def test_meta_keyword_matches(self):
        result = extract_data_js.invoke({"description": "meta tags"})
        assert "meta" in result

    def test_url_keyword_matches(self):
        result = extract_data_js.invoke({"description": "current url"})
        assert "location.href" in result or "href" in result

    def test_unknown_description_returns_fallback(self):
        result = extract_data_js.invoke({"description": "something completely unknown xyz"})
        assert "Custom extraction" in result or "evaluate_script" in result

    def test_unknown_description_lists_available_patterns(self):
        result = extract_data_js.invoke({"description": "something completely unknown xyz"})
        assert "title" in result

    def test_output_is_string(self):
        result = extract_data_js.invoke({"description": "links"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestFormFillGuide:
    def test_output_contains_description(self):
        result = form_fill_guide.invoke({"form_description": "login form with email and password"})
        assert "login form with email and password" in result

    def test_output_mentions_take_snapshot(self):
        result = form_fill_guide.invoke({"form_description": "any form"})
        assert "take_snapshot" in result

    def test_output_mentions_uid(self):
        result = form_fill_guide.invoke({"form_description": "any form"})
        assert "uid" in result.lower()

    def test_output_mentions_fill(self):
        result = form_fill_guide.invoke({"form_description": "any form"})
        assert "fill" in result

    def test_output_mentions_click(self):
        result = form_fill_guide.invoke({"form_description": "any form"})
        assert "click" in result

    def test_output_is_string(self):
        result = form_fill_guide.invoke({"form_description": "test"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestHandleBotDetection:
    def test_output_contains_site_name(self):
        result = handle_bot_detection.invoke({"site_name": "Google"})
        assert "Google" in result

    def test_output_mentions_headless(self):
        result = handle_bot_detection.invoke({"site_name": "example.com"})
        assert "headless" in result.lower()

    def test_output_mentions_mitigations(self):
        result = handle_bot_detection.invoke({"site_name": "Skyscanner"})
        assert "MITIGATION" in result or "mitigation" in result.lower()

    def test_output_is_string(self):
        result = handle_bot_detection.invoke({"site_name": "test"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestDebugPage:
    def test_output_is_string(self):
        result = debug_page.invoke({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_mentions_console(self):
        result = debug_page.invoke({})
        assert "console" in result.lower()

    def test_output_mentions_network(self):
        result = debug_page.invoke({})
        assert "network" in result.lower()

    def test_output_mentions_snapshot(self):
        result = debug_page.invoke({})
        assert "snapshot" in result.lower() or "take_snapshot" in result

    def test_output_mentions_screenshot(self):
        result = debug_page.invoke({})
        assert "screenshot" in result.lower()

    def test_output_is_checklist(self):
        result = debug_page.invoke({})
        # The debug checklist has numbered steps
        assert "1." in result


class TestMultiTabWorkflow:
    def test_output_contains_description(self):
        result = multi_tab_workflow.invoke({"description": "compare two product pages"})
        assert "compare two product pages" in result

    def test_output_mentions_new_page(self):
        result = multi_tab_workflow.invoke({"description": "open tabs"})
        assert "new_page" in result

    def test_output_mentions_select_page(self):
        result = multi_tab_workflow.invoke({"description": "switch tabs"})
        assert "select_page" in result

    def test_output_mentions_list_pages(self):
        result = multi_tab_workflow.invoke({"description": "list tabs"})
        assert "list_pages" in result

    def test_output_is_string(self):
        result = multi_tab_workflow.invoke({"description": "test"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestPerformanceAuditGuide:
    def test_output_contains_url(self):
        result = performance_audit_guide.invoke({"url": "https://example.com"})
        assert "https://example.com" in result

    def test_output_mentions_navigate(self):
        result = performance_audit_guide.invoke({"url": "https://example.com"})
        assert "navigate_page" in result

    def test_output_mentions_lighthouse(self):
        result = performance_audit_guide.invoke({"url": "https://example.com"})
        assert "lighthouse" in result.lower()

    def test_output_mentions_trace(self):
        result = performance_audit_guide.invoke({"url": "https://example.com"})
        assert "trace" in result.lower()

    def test_output_is_string(self):
        result = performance_audit_guide.invoke({"url": "https://example.com"})
        assert isinstance(result, str)
        assert len(result) > 0
