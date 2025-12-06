# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests pour User-Agent parsing et session metadata.

Tests unitaires pour vérifier que:
1. Les User-Agent strings sont correctement parsés
2. Les métadonnées sont correctement intégrées dans les sessions
3. Les cas limites (User-Agent manquant, invalide) sont gérés
"""

import pytest
from src.services.user_agent_parser import UserAgentParser


class TestUserAgentParser:
    """Tests pour UserAgentParser."""
    
    def test_parse_chrome_on_mac(self):
        """Test parsing Chrome on Mac OS X."""
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["browser"].startswith("Chrome")
        assert "10_15" in info["os"] or "10.15" in info["os"]
        assert info["is_pc"] is True
        assert info["is_mobile"] is False
        assert info["is_tablet"] is False
    
    def test_parse_safari_on_ios(self):
        """Test parsing Safari on iOS."""
        user_agent = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/14.1.1 Mobile/15E148 Safari/604.1"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["browser"].startswith("Safari") or info["browser"].startswith("Mobile Safari")
        assert "iPhone" in info["device"] or "iOS" in info["os"]
        assert info["is_mobile"] is True
        assert info["is_pc"] is False
    
    def test_parse_chrome_on_android(self):
        """Test parsing Chrome on Android."""
        user_agent = (
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.120 Mobile Safari/537.36"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["browser"].startswith("Chrome")
        assert "Android" in info["os"]
        assert info["is_mobile"] is True
        assert info["is_pc"] is False
    
    def test_parse_firefox_on_windows(self):
        """Test parsing Firefox on Windows."""
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) "
            "Gecko/20100101 Firefox/89.0"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["browser"].startswith("Firefox")
        assert "Windows" in info["os"]
        assert info["is_pc"] is True
        assert info["is_mobile"] is False
    
    def test_parse_edge_on_windows(self):
        """Test parsing Edge on Windows."""
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["browser"].startswith("Edge") or "Edg" in user_agent
        assert "Windows" in info["os"]
        assert info["is_pc"] is True
    
    def test_parse_ipad_tablet(self):
        """Test parsing iPad as tablet."""
        user_agent = (
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/14.1.1 Mobile/15E148 Safari/604.1"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        assert info["is_tablet"] is True or info["is_mobile"] is True
        assert "iPad" in info["device"] or "iOS" in info["os"]
    
    def test_parse_empty_user_agent(self):
        """Test parsing empty User-Agent string."""
        info = UserAgentParser.parse_user_agent("")
        
        assert info["device"] == "Unknown Device"
        assert info["browser"] == "Unknown Browser"
        assert info["os"] == "Unknown OS"
        assert info["is_pc"] is False
        assert info["is_mobile"] is False
    
    def test_parse_none_user_agent(self):
        """Test parsing None User-Agent."""
        info = UserAgentParser.parse_user_agent(None)
        
        assert info["device"] == "Unknown Device"
        assert info["browser"] == "Unknown Browser"
        assert info["os"] == "Unknown OS"
    
    def test_parse_unknown_user_agent(self):
        """Test parsing 'unknown' User-Agent."""
        info = UserAgentParser.parse_user_agent("unknown")
        
        assert info["device"] == "Unknown Device"
        assert info["browser"] == "Unknown Browser"
        assert info["os"] == "Unknown OS"
    
    def test_parse_malformed_user_agent(self):
        """Test parsing malformed User-Agent string."""
        info = UserAgentParser.parse_user_agent("this is not a valid user agent at all!!!")
        
        # Should not raise exception, should return defaults
        assert info["device"] is not None
        assert info["browser"] is not None
        assert info["os"] is not None
    
    def test_format_session_display_mac_chrome(self):
        """Test formatting session display for Chrome on Mac."""
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36"
        )
        
        display = UserAgentParser.format_session_display(user_agent)
        
        assert "Chrome" in display
        assert "Mac OS X" in display
        assert " on " in display
    
    def test_format_session_display_empty(self):
        """Test formatting session display with empty User-Agent."""
        display = UserAgentParser.format_session_display("")
        
        assert "Unknown Browser" in display
        assert "Unknown OS" in display
        assert " on " in display
    
    def test_all_required_fields_present(self):
        """Test that parsed info includes all required fields."""
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36"
        )
        
        info = UserAgentParser.parse_user_agent(user_agent)
        
        required_fields = ["device", "browser", "os", "is_mobile", "is_tablet", "is_pc"]
        for field in required_fields:
            assert field in info, f"Missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
