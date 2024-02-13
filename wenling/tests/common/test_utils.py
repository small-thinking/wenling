"""Test the utils.
Run test: poetry run pytest wenling/tests/common/test_utils.py
"""

from unittest.mock import MagicMock, patch

import pytest

from wenling.common.utils import *


@pytest.mark.parametrize(
    "input, expected",
    [(1681684094, "2023-04-16 15:28:14")],
)
def test_get_datetime(input, expected):
    assert get_datetime(input) == expected


@pytest.mark.parametrize(
    "url, status_code, expected",
    [
        ("https://example.com", 200, True),
        ("https://example.com", 404, False),
        ("https://example.invalid", None, False),
    ],
)
def test_check_url_exists(url, status_code, expected):
    with patch("requests.get", return_value=MagicMock(status_code=status_code)) as mock_get:
        assert check_url_exists(url) == expected
        mock_get.assert_called_once_with(url)


@pytest.mark.parametrize(
    "responses, css_selector, should_raise_exception, expected_html",
    [
        # Success case without CSS selector, simple body content
        ([MagicMock(status_code=200, text="<body>Simple Content</body>")], "", False, "<body>Simple Content</body>"),
        # Success case with CSS selector, specific div content
        (
            [MagicMock(status_code=200, text="<div>Div Content</div><div>Other Content</div>")],
            "div",
            False,
            "<div>Div Content</div>",
        ),
        # Success case with CSS selector, nested content
        (
            [MagicMock(status_code=200, text="<div><span>Nested Content</span></div>")],
            "span",
            False,
            "<span>Nested Content</span>",
        ),
        # Server error (500), should retry and then succeed
        (
            [MagicMock(status_code=500), MagicMock(status_code=200, text="<body>Retry Success</body>")],
            "",
            False,
            "<body>Retry Success</body>",
        ),
        # Not found error (404), with retries
        ([MagicMock(status_code=404), MagicMock(status_code=404), MagicMock(status_code=404)], "", True, None),
        # CSS selector not found, should return None
        ([MagicMock(status_code=200, text="<body><div>No Match</div></body>")], "section", False, None),
    ],
)
def test_fetch_url_content(responses, css_selector, should_raise_exception, expected_html):
    with patch("requests.get", side_effect=responses) as mock_get:
        if should_raise_exception:
            with pytest.raises(Exception) as excinfo:
                fetch_url_content("http://example.com", css_selector)
            assert "Failed to fetch content" in str(excinfo.value)
        else:
            result = fetch_url_content("http://example.com", css_selector)
            if not expected_html:
                assert result is None
            else:
                assert BeautifulSoup(result, "html.parser") == BeautifulSoup(expected_html, "html.parser")

        assert mock_get.call_count == len(responses)
