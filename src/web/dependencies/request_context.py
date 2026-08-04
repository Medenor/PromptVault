# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Request metadata dependencies (client IP, User-Agent).

Dependencies:
    - get_client_ip(): Extracts client IP address with proxy support
    - get_user_agent(): Extracts User-Agent header
"""

from fastapi import Request

# ============================================================================
# Request Metadata Dependencies
# ============================================================================


def get_client_ip(request: Request) -> str:
    """Extract client IP address with proxy support.

    This dependency extracts the client's IP address from the request,
    handling common proxy headers (X-Forwarded-For, X-Real-IP) used by
    reverse proxies like Nginx, Cloudflare, and AWS ALB.

    Args:
        request: FastAPI request object (injected)

    Returns:
        str: Client IP address (IPv4 or IPv6)

    Priority Order:
        1. X-Forwarded-For (first IP in list)
        2. X-Real-IP
        3. request.client.host (direct connection)
        4. "unknown" (fallback)

    Example:
        >>> @router.post("/auth/login")
        >>> def login(
        ...     credentials: LoginRequest,
        ...     ip_address: str = Depends(get_client_ip),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     # Log login attempt with IP address
        ...     logger.info(f"Login attempt from {ip_address}")
        ...     # Store IP in session for security tracking
        ...     session = create_session(user_id, ip_address=ip_address)
        ...     return {"token": "..."}

    Security Notes:
        - X-Forwarded-For can be spoofed by malicious clients
        - Only trust these headers if behind a reverse proxy
        - For rate limiting, consider hashing IP addresses
        - IPv6 addresses may include privacy extensions
        - "unknown" indicates IP could not be determined
    """
    # X-Forwarded-For header (set by reverse proxies)
    # Format: "client, proxy1, proxy2"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP (client) from comma-separated list
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    # X-Real-IP header (alternative to X-Forwarded-For)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Direct connection (no proxy)
    if request.client and request.client.host:
        return request.client.host

    # Fallback if IP cannot be determined
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract User-Agent header from request.

    This dependency extracts and truncates the User-Agent string, which
    identifies the client software (browser, mobile app, API client).
    Useful for session tracking, analytics, and security monitoring.

    Args:
        request: FastAPI request object (injected)

    Returns:
        str: User-Agent string (truncated to 255 chars)

    Example:
        >>> @router.post("/auth/login")
        >>> def login(
        ...     credentials: LoginRequest,
        ...     user_agent: str = Depends(get_user_agent),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     # Store user agent in session
        ...     session = create_session(
        ...         user_id,
        ...         user_agent=user_agent
        ...     )
        ...     return {"token": "..."}
        >>>
        >>> @router.get("/sessions")
        >>> def list_sessions(
        ...     user: User = Depends(get_current_active_user),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     sessions = get_user_sessions(user.id, db)
        ...     # Each session includes user_agent for identification
        ...     return {"sessions": sessions}

    Security Notes:
        - User-Agent can be spoofed by clients
        - Truncated to 255 chars to prevent database overflow
        - "unknown" if header is missing
        - Useful for detecting suspicious sessions (different device)
        - Consider parsing for browser/OS detection
    """
    user_agent = request.headers.get("User-Agent", "unknown")

    # Truncate to 255 characters to fit database column
    if len(user_agent) > 255:
        user_agent = user_agent[:255]

    return user_agent
