"""Test the utils.
Run test: poetry run pytest wenling/tests/common/test_utils.py
"""
from unittest.mock import MagicMock, patch

import pytest

from wenling.common.utils import *


@pytest.mark.parametrize(
    "input, expected",
    [(1681684094, "2023-04-16 14:28:14")],
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
    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = status_code
        result = check_url_exists(url)
        assert result == expected


@pytest.mark.parametrize(
    "responses, expected, call_count",
    [
        # Success case
        ([MagicMock(status_code=200, text="Sample Content")], "Sample Content", 1),
        # Failure case
        ([MagicMock(status_code=404)], Exception, 1),
        # Retry case (initial failure followed by success)
        ([MagicMock(status_code=500), MagicMock(status_code=200, text="Retry Success")], "Retry Success", 2),
    ],
)
def test_fetch_url_content(responses, expected, call_count):
    with patch("requests.get", side_effect=responses) as mock_get:
        if isinstance(expected, Exception):
            with pytest.raises(Exception) as excinfo:
                fetch_url_content("http://example.com")
            assert "Failed to fetch Markdown content" in str(excinfo.value)
        else:
            result = fetch_url_content("http://example.com")
            assert result == expected

        assert mock_get.call_count == call_count
