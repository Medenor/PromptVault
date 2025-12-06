# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Example FastAPI application with rate limiting.

This example demonstrates how to integrate the rate limiting middleware
into a FastAPI application with authentication endpoints.

Usage:
    python examples/rate_limit_example.py

Then test with:
    # Test login rate limit (5 requests per 15 minutes)
    for i in {1..6}; do
        curl -X POST http://localhost:8000/api/auth/login \
            -H "Content-Type: application/json" \
            -d '{"username":"test","password":"test"}'
        echo ""
        sleep 1
    done
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
import uvicorn

from src.web.middleware import (
    limiter,
    rate_limit_exceeded_handler,
    auth_login_limit,
    auth_register_limit,
    password_reset_limit,
    api_limit,
    admin_limit,
)

# Create FastAPI app
app = FastAPI(
    title="PromptVault Rate Limiting Example",
    description="Example application demonstrating rate limiting middleware",
    version="1.0.0",
)

# Add limiter to app state (required by slowapi)
app.state.limiter = limiter

# Register rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request model."""
    username: str
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


# Authentication Endpoints (with rate limiting)

@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit(auth_login_limit)
async def login(request: Request, credentials: LoginRequest):
    """Login endpoint with rate limiting.

    Rate limit: 5 attempts per 15 minutes (configurable)

    Returns:
        TokenResponse with access token

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Simulate authentication logic
    if credentials.username == "test" and credentials.password == "test":
        return TokenResponse(access_token="fake_token_123")

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/auth/register")
@limiter.limit(auth_register_limit)
async def register(request: Request, user_data: RegisterRequest):
    """Registration endpoint with rate limiting.

    Rate limit: 3 attempts per hour (configurable)

    Returns:
        User ID and success message

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Simulate registration logic
    return {
        "user_id": "new_user_123",
        "username": user_data.username,
        "email": user_data.email,
        "message": "Registration successful",
    }


@app.post("/api/auth/password-reset")
@limiter.limit(password_reset_limit)
async def request_password_reset(request: Request, reset_data: PasswordResetRequest):
    """Password reset request endpoint with rate limiting.

    Rate limit: 3 attempts per hour (configurable)

    Returns:
        Success message

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Simulate password reset logic
    return {
        "message": f"Password reset email sent to {reset_data.email}",
        "email": reset_data.email,
    }


# General API Endpoints (with rate limiting)

@app.get("/api/prompts")
@limiter.limit(api_limit)
async def get_prompts(request: Request):
    """Get prompts endpoint with rate limiting.

    Rate limit: 100 requests per minute

    Returns:
        List of prompts

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "prompts": [
            {"id": 1, "title": "Example Prompt 1", "content": "..."},
            {"id": 2, "title": "Example Prompt 2", "content": "..."},
        ]
    }


@app.post("/api/prompts")
@limiter.limit(api_limit)
async def create_prompt(request: Request):
    """Create prompt endpoint with rate limiting.

    Rate limit: 100 requests per minute

    Returns:
        Created prompt

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "id": 3,
        "title": "New Prompt",
        "content": "...",
        "created_at": "2024-01-01T00:00:00Z",
    }


# Admin Endpoints (with higher rate limits)

@app.get("/api/admin/users")
@limiter.limit(admin_limit)
async def get_users(request: Request):
    """Get users endpoint with higher rate limiting.

    Rate limit: 200 requests per minute (higher for admin)

    Returns:
        List of users

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "users": [
            {"id": 1, "username": "user1", "email": "user1@example.com"},
            {"id": 2, "username": "user2", "email": "user2@example.com"},
        ]
    }


@app.get("/api/admin/stats")
@limiter.limit(admin_limit)
async def get_stats(request: Request):
    """Get statistics endpoint with higher rate limiting.

    Rate limit: 200 requests per minute (higher for admin)

    Returns:
        Application statistics

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "total_users": 100,
        "total_prompts": 500,
        "total_requests": 10000,
    }


# Custom Rate Limit Examples

@app.post("/api/expensive-operation")
@limiter.limit("5/hour")  # Custom: 5 requests per hour
async def expensive_operation(request: Request):
    """Expensive operation with strict rate limiting.

    Rate limit: 5 requests per hour (custom)

    Returns:
        Operation result

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "status": "completed",
        "message": "Expensive operation completed successfully",
    }


@app.post("/api/quick-operation")
@limiter.limit("10/second")  # Custom: 10 requests per second
async def quick_operation(request: Request):
    """Quick operation with high rate limit.

    Rate limit: 10 requests per second (custom)

    Returns:
        Operation result

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return {
        "status": "completed",
        "message": "Quick operation completed successfully",
    }


# Health Check (no rate limiting)

@app.get("/health")
async def health_check():
    """Health check endpoint without rate limiting.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "rate-limit-example"}


# Root Endpoint

@app.get("/")
async def root():
    """Root endpoint with API information.

    Returns:
        API information and available endpoints
    """
    return {
        "name": "PromptVault Rate Limiting Example",
        "version": "1.0.0",
        "endpoints": {
            "authentication": {
                "/api/auth/login": "5 requests per 15 minutes",
                "/api/auth/register": "3 requests per hour",
                "/api/auth/password-reset": "3 requests per hour",
            },
            "api": {
                "/api/prompts": "100 requests per minute",
            },
            "admin": {
                "/api/admin/users": "200 requests per minute",
                "/api/admin/stats": "200 requests per minute",
            },
            "custom": {
                "/api/expensive-operation": "5 requests per hour",
                "/api/quick-operation": "10 requests per second",
            },
        },
        "note": "Rate limits are enforced per IP address for unauthenticated requests, and per user ID for authenticated requests.",
    }


if __name__ == "__main__":
    print("Starting PromptVault Rate Limiting Example...")
    print("Server will be available at http://localhost:8000")
    print("\nTry these commands to test rate limiting:\n")
    print("# Test login rate limit (should block after 5 requests):")
    print('for i in {1..6}; do curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\'; echo ""; sleep 1; done\n')
    print("# Check API documentation:")
    print("curl http://localhost:8000/docs\n")

    uvicorn.run(
        "examples.rate_limit_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
