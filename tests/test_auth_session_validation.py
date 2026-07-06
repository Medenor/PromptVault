# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pytest-compatible tests for AUTH-SESSION features.

Tests the user session management metadata and parsing.
"""

import pytest
from src.services.user_agent_parser import UserAgentParser


class TestUserAgentParser:
    """Test UserAgentParser service."""

    def test_parse_chrome_on_mac(self):
        """Test parsing Chrome on Mac OS X."""
        parser = UserAgentParser()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        info = parser.parse_user_agent(ua)

        assert info["device"] == "Desktop"
        assert "Chrome" in info["browser"]
        assert "Mac OS X" in info["os"]

    def test_parse_safari_on_iphone(self):
        """Test parsing Safari on iPhone."""
        parser = UserAgentParser()
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
        info = parser.parse_user_agent(ua)

        assert info["is_mobile"] is True
        assert "Safari" in info["browser"]
        assert "iOS" in info["os"]

    def test_parse_firefox_on_windows(self):
        """Test parsing Firefox on Windows."""
        parser = UserAgentParser()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        info = parser.parse_user_agent(ua)

        assert "Firefox" in info["browser"]
        assert "Windows" in info["os"]

    def test_parse_empty_user_agent(self):
        """Test parsing empty User-Agent string."""
        parser = UserAgentParser()
        info = parser.parse_user_agent("")

        assert info["device"] == "Unknown Device"
        assert info["browser"] == "Unknown Browser"
        assert info["os"] == "Unknown OS"

    def test_parse_none_user_agent(self):
        """Test parsing None User-Agent."""
        parser = UserAgentParser()
        info = parser.parse_user_agent(None)

        assert info["device"] == "Unknown Device"
        assert info["browser"] == "Unknown Browser"
        assert info["os"] == "Unknown OS"

    def test_all_fields_present(self):
        """Test that all required fields are present in response."""
        parser = UserAgentParser()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0"
        info = parser.parse_user_agent(ua)

        assert "device" in info
        assert "browser" in info
        assert "os" in info
        assert "is_mobile" in info
        assert "is_tablet" in info
        assert "is_pc" in info

    def test_format_session_display(self):
        """Test session display formatting."""
        parser = UserAgentParser()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0"
        display = parser.format_session_display(ua)

        assert " on " in display
        assert len(display) > 0

    def test_format_empty_user_agent_display(self):
        """Test session display with empty User-Agent."""
        parser = UserAgentParser()
        display = parser.format_session_display("")

        assert display  # Should not be empty
        assert "Unknown" in display
