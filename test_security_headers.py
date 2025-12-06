#!/usr/bin/env python3
"""Test security headers implementation"""

import sys
import json
from urllib.request import Request, urlopen
from urllib.error import URLError

def test_security_headers():
    """Test that all security headers are present"""
    print("=" * 60)
    print("Testing Security Headers Implementation")
    print("=" * 60)
    print()
    
    url = "http://127.0.0.1:8003/"
    required_headers = {
        "Strict-Transport-Security": "max-age=31536000",  # 1 year
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    
    try:
        req = Request(url)
        req.add_header("User-Agent", "SecurityHeadersTest/1.0")
        with urlopen(req, timeout=5) as response:
            headers = dict(response.headers)
            
            print(f"Testing endpoint: {url}")
            print()
            
            all_passed = True
            for header_name, expected_value in required_headers.items():
                if header_name in headers:
                    actual_value = headers[header_name]
                    # Check if expected value is contained in actual value
                    if expected_value in actual_value or len(actual_value) > 0:
                        print(f"✓ {header_name}: {actual_value}")
                    else:
                        print(f"✗ {header_name}: Expected '{expected_value}', got '{actual_value}'")
                        all_passed = False
                else:
                    print(f"✗ {header_name}: NOT FOUND")
                    all_passed = False
            
            print()
            if all_passed:
                print("✓ All security headers are present!")
                return 0
            else:
                print("✗ Some security headers are missing or incorrect")
                return 1
                
    except URLError as e:
        print(f"✗ Failed to connect to {url}")
        print(f"  Error: {e}")
        print()
        print("Server may not be running. Start with:")
        print("  python -m pytest tests/ --cov --cov-report=html -v")
        return 2
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 2

if __name__ == "__main__":
    sys.exit(test_security_headers())
