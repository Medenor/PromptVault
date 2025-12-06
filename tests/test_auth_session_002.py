# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for AUTH-SESSION-002 - Session Metadata Accuracy.

Verify that session metadata (device, browser, OS) are correctly parsed and returned by the API.
"""

import json
from datetime import datetime, timedelta
from src.services.user_agent_parser import UserAgentParser


def test_auth_session_002_metadata_accuracy():
    """AUTH-SESSION-002: Verify session metadata parsing accuracy.

    Test criteria:
    1. Device, browser, and OS metadata must be parsed correctly.
    2. Edge cases should be handled gracefully.
    3. The response format should include all required fields.
    """
    
    test_cases = [
        {
            "name": "Chrome on Mac OS X",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "expected_browser": "Chrome",
            "expected_os_contains": ["Mac OS X", "10_15", "10.15"],
            "expected_device": "Desktop",
        },
        {
            "name": "Safari on iPhone",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
            "expected_browser": ["Safari", "Mobile Safari"],
            "expected_os_contains": ["iOS", "14"],
            "is_mobile": True,
        },
        {
            "name": "Empty User-Agent",
            "user_agent": "",
            "expected_device": "Unknown Device",
            "expected_browser": "Unknown Browser",
            "expected_os": "Unknown OS",
        },
        {
            "name": "None User-Agent",
            "user_agent": None,
            "expected_device": "Unknown Device",
            "expected_browser": "Unknown Browser",
            "expected_os": "Unknown OS",
        },
    ]
    
    parser = UserAgentParser()
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        case_name = test_case["name"]
        user_agent = test_case["user_agent"]
        
        try:
            info = parser.parse_user_agent(user_agent)
            
            # Verify all required fields are present
            assert "device" in info, f"{case_name}: Missing 'device' field"
            assert "browser" in info, f"{case_name}: Missing 'browser' field"
            assert "os" in info, f"{case_name}: Missing 'os' field"
            assert "is_mobile" in info, f"{case_name}: Missing 'is_mobile' field"
            assert "is_tablet" in info, f"{case_name}: Missing 'is_tablet' field"
            assert "is_pc" in info, f"{case_name}: Missing 'is_pc' field"
            
            # Check expected browser
            if "expected_browser" in test_case:
                expected = test_case["expected_browser"]
                if isinstance(expected, list):
                    assert any(exp in info["browser"] for exp in expected), \
                        f"{case_name}: Browser '{info['browser']}' doesn't match any of {expected}"
                else:
                    assert expected in info["browser"], \
                        f"{case_name}: Browser '{info['browser']}' doesn't contain '{expected}'"
            
            # Check expected OS contains substring
            if "expected_os_contains" in test_case:
                expected_os_contains = test_case["expected_os_contains"]
                assert any(exp in info["os"] for exp in expected_os_contains), \
                    f"{case_name}: OS '{info['os']}' doesn't contain any of {expected_os_contains}"
            
            # Check expected device
            if "expected_device" in test_case:
                expected_device = test_case["expected_device"]
                assert info["device"] == expected_device, \
                    f"{case_name}: Device '{info['device']}' != '{expected_device}'"
            
            # Check expected browser exact match
            if "expected_browser" in test_case and isinstance(test_case["expected_browser"], str):
                pass  # Already checked above
            
            # Check expected OS exact match
            if "expected_os" in test_case:
                assert info["os"] == test_case["expected_os"], \
                    f"{case_name}: OS '{info['os']}' != '{test_case['expected_os']}'"
            
            # Check is_mobile flag
            if "is_mobile" in test_case:
                assert info["is_mobile"] == test_case["is_mobile"], \
                    f"{case_name}: is_mobile={info['is_mobile']} != {test_case['is_mobile']}"
            
            print(f"✓ {case_name}")
            print(f"  Device: {info['device']}")
            print(f"  Browser: {info['browser']}")
            print(f"  OS: {info['os']}")
            passed += 1
        
        except AssertionError as e:
            print(f"✗ {case_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {case_name}: Unexpected error: {e}")
            failed += 1
    
    print(f"\n\n=== Test Results ===")
    print(f"Passed: {passed}/{len(test_cases)}")
    print(f"Failed: {failed}/{len(test_cases)}")
    
    assert failed == 0, f"{failed} test(s) failed"
    return True


def test_format_session_display():
    """Test UserAgentParser.format_session_display formatting."""
    
    parser = UserAgentParser()
    
    # Test normal case
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36"
    display = parser.format_session_display(user_agent)
    
    assert " on " in display, f"Display string missing ' on ': {display}"
    print(f"✓ Display format: {display}")


if __name__ == "__main__":
    print("Running AUTH-SESSION-002 tests...\n")
    test_auth_session_002_metadata_accuracy()
    test_format_session_display()
    print("\n✅ All AUTH-SESSION-002 tests passed!")
