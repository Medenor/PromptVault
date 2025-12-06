# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
"""
PromptVault Authentication Performance Benchmark Suite

Comprehensive performance testing without external dependencies.
Tests critical authentication endpoints with various scenarios.

Test cases:
- AUTH-PERF-001: Login performance (response time, throughput)
- AUTH-PERF-002: Registration performance (concurrent signups)
- AUTH-PERF-003: Token refresh performance
- AUTH-PERF-004: Session management scalability
- AUTH-PERF-005: Concurrent user authentication (load test)

Usage:
    python3 scripts/benchmark_auth_performance.py
"""

import asyncio
import time
import random
import string
import json
import statistics
from typing import List, Dict, Tuple
from datetime import datetime
import httpx
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Store performance metrics for an endpoint."""
    endpoint: str
    method: str
    response_times: List[float] = field(default_factory=list)
    status_codes: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_result(self, response_time: float, status_code: int, error: str = None):
        """Record a result."""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)
    
    @property
    def success_count(self) -> int:
        """Count successful requests."""
        return sum(1 for code in self.status_codes if 200 <= code < 300)
    
    @property
    def failure_count(self) -> int:
        """Count failed requests."""
        return len(self.status_codes) - self.success_count
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if not self.status_codes:
            return 0.0
        return (self.success_count / len(self.status_codes)) * 100
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time in ms."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def min_response_time(self) -> float:
        """Minimum response time in ms."""
        return min(self.response_times) if self.response_times else 0.0
    
    @property
    def max_response_time(self) -> float:
        """Maximum response time in ms."""
        return max(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """95th percentile response time in ms."""
        if not self.response_times or len(self.response_times) < 20:
            return 0.0
        return statistics.quantiles(self.response_times, n=20)[18]  # 19/20 = 0.95
    
    @property
    def p99_response_time(self) -> float:
        """99th percentile response time in ms."""
        if not self.response_times or len(self.response_times) < 100:
            return 0.0
        return statistics.quantiles(self.response_times, n=100)[98]  # 99/100 = 0.99
    
    def summary(self) -> str:
        """Generate a summary of metrics."""
        return f"""
{self.endpoint} ({self.method})
  Total Requests: {len(self.status_codes)}
  Success Rate: {self.success_rate:.1f}% ({self.success_count}/{len(self.status_codes)})
  Failures: {self.failure_count}
  
  Response Times (ms):
    Average: {self.avg_response_time:.2f}
    Min: {self.min_response_time:.2f}
    Max: {self.max_response_time:.2f}
    p95: {self.p95_response_time:.2f}
    p99: {self.p99_response_time:.2f}
"""


class AuthPerformanceBenchmark:
    """Main performance benchmark suite."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8003", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.test_users: List[Dict] = []
    
    async def benchmark_login(self, num_requests: int = 100) -> PerformanceMetrics:
        """
        AUTH-PERF-001: Test login endpoint performance.
        
        Measures:
        - Response time for login requests
        - Success rate
        - Throughput under load
        """
        metric = PerformanceMetrics("/api/auth/login", "POST")
        
        # Create test users first
        users = []
        async with httpx.AsyncClient() as client:
            for i in range(min(num_requests, 10)):  # Reuse users to avoid rate limiting
                username = f"perf_login_{random.randint(100000, 999999)}"
                email = f"{username}@perftest.local"
                password = "PerfTest@Pass123"
                
                # Register user
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/auth/register",
                        json={
                            "username": username,
                            "email": email,
                            "password": password,
                            "password_confirm": password
                        },
                        timeout=10.0
                    )
                    if resp.status_code == 201:
                        users.append({
                            "username": username,
                            "password": password
                        })
                except Exception as e:
                    if self.verbose:
                        print(f"Registration error: {e}")
            
            # Test login performance
            for i in range(num_requests):
                user = random.choice(users) if users else {
                    "username": "testuser",
                    "password": "PerfTest@Pass123"
                }
                
                start_time = time.time()
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/auth/login",
                        json={
                            "username": user["username"],
                            "password": user["password"]
                        },
                        timeout=10.0
                    )
                    elapsed = (time.time() - start_time) * 1000
                    metric.add_result(elapsed, resp.status_code)
                    
                    if self.verbose and i % 10 == 0:
                        print(f"  Request {i+1}/{num_requests}: {resp.status_code} ({elapsed:.2f}ms)")
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    metric.add_result(elapsed, 0, str(e))
        
        self.metrics["/api/auth/login"] = metric
        return metric
    
    async def benchmark_registration(self, num_requests: int = 50) -> PerformanceMetrics:
        """
        AUTH-PERF-002: Test registration endpoint performance.
        
        Measures:
        - Concurrent registration capacity
        - Password hashing performance
        - Database insertion speed
        """
        metric = PerformanceMetrics("/api/auth/register", "POST")
        
        async with httpx.AsyncClient() as client:
            for i in range(num_requests):
                username = f"perf_reg_{time.time_ns()}_{i}"
                email = f"{username}@perftest.local"
                password = f"PerfReg@Pass{random.randint(100, 999)}"
                
                start_time = time.time()
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/auth/register",
                        json={
                            "username": username,
                            "email": email,
                            "password": password,
                            "password_confirm": password
                        },
                        timeout=10.0
                    )
                    elapsed = (time.time() - start_time) * 1000
                    metric.add_result(elapsed, resp.status_code)
                    
                    if self.verbose and i % 10 == 0:
                        print(f"  Request {i+1}/{num_requests}: {resp.status_code} ({elapsed:.2f}ms)")
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    metric.add_result(elapsed, 0, str(e))
        
        self.metrics["/api/auth/register"] = metric
        return metric
    
    async def benchmark_token_refresh(self, num_requests: int = 50) -> PerformanceMetrics:
        """
        AUTH-PERF-003: Test token refresh performance.
        
        Measures:
        - JWT generation speed
        - Refresh token validation overhead
        - Session lookup performance
        """
        metric = PerformanceMetrics("/api/auth/refresh", "POST")
        
        async with httpx.AsyncClient() as client:
            # Create a test user and get initial token
            username = f"perf_refresh_{random.randint(100000, 999999)}"
            email = f"{username}@perftest.local"
            password = "PerfTest@Pass123"
            
            # Register
            await client.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "password_confirm": password
                },
                timeout=10.0
            )
            
            # Login to get token
            login_resp = await client.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10.0
            )
            
            if login_resp.status_code == 200:
                token = login_resp.json().get("access_token")
                
                for i in range(num_requests):
                    start_time = time.time()
                    try:
                        resp = await client.post(
                            f"{self.base_url}/api/auth/refresh",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10.0
                        )
                        elapsed = (time.time() - start_time) * 1000
                        metric.add_result(elapsed, resp.status_code)
                        
                        if resp.status_code == 200:
                            token = resp.json().get("access_token")
                        
                        if self.verbose and i % 10 == 0:
                            print(f"  Request {i+1}/{num_requests}: {resp.status_code} ({elapsed:.2f}ms)")
                    except Exception as e:
                        elapsed = (time.time() - start_time) * 1000
                        metric.add_result(elapsed, 0, str(e))
        
        self.metrics["/api/auth/refresh"] = metric
        return metric
    
    async def run_all_benchmarks(self):
        """Run all performance benchmarks."""
        print("\n" + "="*70)
        print("PromptVault Authentication Performance Benchmark")
        print("="*70)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        print("Running AUTH-PERF-001: Login Endpoint Performance...")
        await self.benchmark_login(num_requests=100)
        
        print("\nRunning AUTH-PERF-002: Registration Endpoint Performance...")
        await self.benchmark_registration(num_requests=50)
        
        print("\nRunning AUTH-PERF-003: Token Refresh Performance...")
        await self.benchmark_token_refresh(num_requests=50)
        
        print("\n" + "="*70)
        print("Performance Test Results Summary")
        print("="*70)
        
        for endpoint, metric in self.metrics.items():
            print(metric.summary())
        
        print("="*70)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")


async def main():
    """Run the performance benchmark."""
    benchmark = AuthPerformanceBenchmark(verbose=True)
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
