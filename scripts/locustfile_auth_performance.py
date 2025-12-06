# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Locust Performance Testing Suite for PromptVault Authentication

This module provides comprehensive load testing and performance benchmarking
for authentication endpoints using Locust framework.

Test scenarios include:
- AUTH-PERF-001: Login endpoint load testing
- AUTH-PERF-002: Registration endpoint load testing
- AUTH-PERF-003: Token refresh performance
- AUTH-PERF-004: Session management scalability
- AUTH-PERF-005: Concurrent user authentication

Usage:
    locust -f scripts/locustfile_auth_performance.py --host=http://127.0.0.1:8003
"""

import time
import random
import string
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


class AuthPerformanceUser(FastHttpUser):
    """Fast HTTP user for authentication performance testing."""
    
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.username = None
        self.email = None
        self.password = "PerfTest@Pass123"
    
    def on_start(self):
        """Register a new test user at the start."""
        self.username = f"perftest_{random.randint(100000, 999999)}"
        self.email = f"{self.username}@perftest.local"
        
        with self.client.post(
            "/api/auth/register",
            json={
                "username": self.username,
                "email": self.email,
                "password": self.password,
                "password_confirm": self.password
            },
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    @task(4)
    def login(self):
        """
        AUTH-PERF-001: Test login endpoint performance.
        
        Measures:
        - Response time for login requests
        - Success rate
        - Token generation time
        """
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": self.username,
                "password": self.password
            },
            name="/api/auth/login"
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                self.token = data["access_token"]
    
    @task(2)
    def get_profile(self):
        """
        AUTH-PERF-004: Test authenticated endpoint performance.
        
        Measures:
        - Response time for authorized requests
        - Token validation overhead
        - Session lookup performance
        """
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get(
                "/api/auth/me",
                headers=headers,
                name="/api/auth/me"
            )
    
    @task(1)
    def refresh_token(self):
        """
        AUTH-PERF-003: Test token refresh performance.
        
        Measures:
        - Token refresh response time
        - JWT generation performance
        - Refresh token validation overhead
        """
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.client.post(
                "/api/auth/refresh",
                headers=headers,
                name="/api/auth/refresh"
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.token = data["access_token"]
    
    @task(1)
    def logout(self):
        """
        AUTH-PERF-005: Test logout endpoint performance.
        
        Measures:
        - Session cleanup response time
        - Token revocation overhead
        """
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.post(
                "/api/auth/logout",
                headers=headers,
                name="/api/auth/logout"
            )
            self.token = None


class AuthRegistrationStress(FastHttpUser):
    """
    AUTH-PERF-002: Registration endpoint stress test.
    
    Focuses specifically on registration performance under load.
    """
    
    wait_time = between(2, 5)
    
    @task
    def register(self):
        """Test registration endpoint under concurrent load."""
        username = f"regtest_{time.time()}_{random.randint(0, 9999)}"
        email = f"{username}@regtest.local"
        password = f"RegTest@Pass{random.randint(100, 999)}"
        
        self.client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "password_confirm": password
            },
            name="/api/auth/register"
        )


class SessionManagementTest(FastHttpUser):
    """
    AUTH-PERF-004: Session management and scalability test.
    
    Tests concurrent session creation, management, and cleanup.
    """
    
    wait_time = between(1, 2)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.username = None
        self.sessions = []
    
    def on_start(self):
        """Create a test user."""
        self.username = f"sesstest_{random.randint(100000, 999999)}"
        email = f"{self.username}@sesstest.local"
        password = "SessTest@Pass123"
        
        self.client.post(
            "/api/auth/register",
            json={
                "username": self.username,
                "email": email,
                "password": password,
                "password_confirm": password
            }
        )
    
    @task(3)
    def create_session(self):
        """Create multiple sessions for the same user."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": self.username,
                "password": "SessTest@Pass123"
            },
            name="/api/auth/login-session"
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                self.sessions.append(data["access_token"])
                self.token = data["access_token"]
    
    @task(2)
    def list_sessions(self):
        """List all sessions for the current user."""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get(
                "/api/admin/sessions",
                headers=headers,
                name="/api/admin/sessions-list"
            )
    
    @task(1)
    def revoke_session(self):
        """Revoke a session and measure performance."""
        if len(self.sessions) > 1 and self.token:
            session_to_revoke = self.sessions.pop(0)
            headers = {"Authorization": f"Bearer {self.token}"}
            
            self.client.delete(
                f"/api/auth/me/sessions/{session_to_revoke}",
                headers=headers,
                name="/api/auth/sessions-revoke"
            )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize performance test metrics."""
    print("\n" + "="*60)
    print("PromptVault Authentication Performance Test Started")
    print("="*60)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count}")
    print(f"Spawn Rate: {environment.runner.spawn_rate} users/sec")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print final performance statistics."""
    print("\n" + "="*60)
    print("Performance Test Summary")
    print("="*60)
    
    for endpoint, stats in environment.stats.items():
        if endpoint[0] == "/api/auth/login":
            print(f"\n{endpoint[0]} ({endpoint[1]}):")
            print(f"  Requests: {stats.num_requests}")
            print(f"  Failures: {stats.num_failures}")
            print(f"  Avg Response Time: {stats.avg_response_time:.2f}ms")
            print(f"  Min Response Time: {stats.min_response_time:.2f}ms")
            print(f"  Max Response Time: {stats.max_response_time:.2f}ms")
            print(f"  p95 Response Time: {stats.get_response_time_percentile(0.95):.2f}ms")
            print(f"  p99 Response Time: {stats.get_response_time_percentile(0.99):.2f}ms")


if __name__ == "__main__":
    print("Start Locust with: locust -f scripts/locustfile_auth_performance.py --host=http://127.0.0.1:8003")
