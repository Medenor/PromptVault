# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Service for parsing User-Agent strings to extract device/browser/OS information.

This module provides utilities to parse User-Agent strings and extract
readable information about the device, browser, and operating system.

Example:
    >>> parser = UserAgentParser()
    >>> info = parser.parse_user_agent(
    ...     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    ...     "AppleWebKit/537.36 Chrome/91.0.4472.124"
    ... )
    >>> info
    {
        'device': 'Desktop',
        'browser': 'Chrome 91.0',
        'os': 'Mac OS X 10.15.7',
        'is_mobile': False,
        'is_tablet': False,
        'is_pc': True
    }
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from user_agents import parse
    HAS_USER_AGENTS = True
except ImportError:
    HAS_USER_AGENTS = False
    logger.warning("user-agents library not installed. User-Agent parsing disabled.")


class UserAgentParser:
    """Parser pour User-Agent strings.
    
    Utilise la bibliothèque user-agents pour parser les User-Agent strings
    et extraire des informations structurées sur le device, browser et OS.
    """
    
    @staticmethod
    def parse_user_agent(user_agent: Optional[str]) -> Dict[str, any]:
        """Parse User-Agent string et extrait les informations.
        
        Args:
            user_agent: User-Agent string brut (ex: Mozilla/5.0...)
            
        Returns:
            Dict avec les clés:
                - device: Type de device (ex: "Desktop", "iPhone 12", "Samsung Galaxy")
                - browser: Nom et version du browser (ex: "Chrome 91.0")
                - os: Système d'exploitation (ex: "Mac OS X 10.15.7")
                - is_mobile: Boolean si mobile
                - is_tablet: Boolean si tablet
                - is_pc: Boolean si desktop
                
        Example:
            >>> info = UserAgentParser.parse_user_agent("Mozilla/5.0...")
            >>> print(info['device'])
            'Desktop'
        """
        if not user_agent or user_agent == "unknown":
            return {
                "device": "Unknown Device",
                "browser": "Unknown Browser",
                "os": "Unknown OS",
                "is_mobile": False,
                "is_tablet": False,
                "is_pc": False,
            }
        
        if not HAS_USER_AGENTS:
            return {
                "device": "Unknown Device",
                "browser": "Unknown Browser",
                "os": "Unknown OS",
                "is_mobile": False,
                "is_tablet": False,
                "is_pc": False,
            }
        
        try:
            ua = parse(user_agent)
            
            # Device type
            if ua.is_mobile:
                device = f"{ua.device.brand or 'Mobile'} {ua.device.model or 'Device'}"
                device = device.strip()
            elif ua.is_tablet:
                device = f"{ua.device.brand or 'Tablet'} {ua.device.model or 'Device'}"
                device = device.strip()
            elif ua.is_pc:
                device = "Desktop"
            else:
                device = "Unknown Device"
            
            # Browser
            if ua.browser.family:
                browser = f"{ua.browser.family}"
                if ua.browser.version_string:
                    browser = f"{browser} {ua.browser.version_string}"
            else:
                browser = "Unknown Browser"
            
            # OS
            if ua.os.family:
                os_name = f"{ua.os.family}"
                if ua.os.version_string:
                    os_name = f"{os_name} {ua.os.version_string}"
            else:
                os_name = "Unknown OS"
            
            return {
                "device": device.strip(),
                "browser": browser.strip(),
                "os": os_name.strip(),
                "is_mobile": ua.is_mobile,
                "is_tablet": ua.is_tablet,
                "is_pc": ua.is_pc,
            }
        
        except Exception as e:
            logger.warning(f"Error parsing User-Agent '{user_agent}': {e}")
            return {
                "device": "Unknown Device",
                "browser": "Unknown Browser",
                "os": "Unknown OS",
                "is_mobile": False,
                "is_tablet": False,
                "is_pc": False,
            }
    
    @staticmethod
    def format_session_display(user_agent: Optional[str]) -> str:
        """Format User-Agent pour affichage UI simple.
        
        Retourne une string formatée comme "Chrome 91.0 on Mac OS X 10.15"
        
        Args:
            user_agent: User-Agent string brut
            
        Returns:
            String formatée pour affichage UI
            
        Example:
            >>> display = UserAgentParser.format_session_display("Mozilla/5.0...")
            >>> print(display)
            'Chrome 91.0 on Mac OS X 10.15'
        """
        info = UserAgentParser.parse_user_agent(user_agent)
        return f"{info['browser']} on {info['os']}"
