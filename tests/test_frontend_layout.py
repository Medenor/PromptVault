"""
Regression tests covering server-rendered layout expectations for the main UI.
"""

from fastapi.testclient import TestClient


def test_sidebar_filters_appear_above_categories(test_client: TestClient) -> None:
    """
    Ensure the sidebar renders the Prompts header and positions filters ahead of
    categories and tags to keep search controls visible without scrolling.
    """
    response = test_client.get("/")
    assert response.status_code == 200

    html = response.text
    prompts_idx = html.find('data-i18n="nav.prompts"')
    filters_idx = html.find('data-i18n="nav.filters"')
    categories_idx = html.find('data-i18n="nav.categories"')
    tags_idx = html.find('data-i18n="nav.tags"')

    assert -1 not in (prompts_idx, filters_idx, categories_idx, tags_idx)
    assert prompts_idx < filters_idx < categories_idx < tags_idx
