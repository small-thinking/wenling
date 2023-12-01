"""Test the utils.
Run test: poetry run pytest tests/common/test_utils.py
"""
from unittest.mock import patch

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
