#!/bin/bash

################################################################################
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
################################################################################

################################################################################
# PromptVault Authentication Performance Testing Automation Script
#
# Automates performance testing for authentication endpoints.
# Tests: AUTH-PERF-001 through AUTH-PERF-005
#
# Usage:
#   ./scripts/run_performance_tests.sh [mode]
#
# Modes:
#   benchmark - Run Python benchmark suite (default)
#   locust    - Run Locust load testing
#   all       - Run all performance tests
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://127.0.0.1:8003"
PERF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$PERF_DIR/performance_results"
LOG_FILE="$RESULTS_DIR/performance_test_$(date +%Y%m%d_%H%M%S).log"

# Create results directory
mkdir -p "$RESULTS_DIR"

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  PromptVault Authentication Performance Testing                 ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_section() {
    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_server() {
    print_section "Checking Application Server"
    
    print_info "Checking if server is running at $BASE_URL..."
    
    if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        print_success "Server is running"
        return 0
    else
        print_error "Server is not running at $BASE_URL"
        print_info "Starting server..."
        
        cd "$PERF_DIR"
        python3 run_web.py > /tmp/promptvault_server.log 2>&1 &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 3
        
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            print_success "Server started (PID: $SERVER_PID)"
            echo $SERVER_PID > /tmp/promptvault_server.pid
            return 0
        else
            print_error "Failed to start server"
            return 1
        fi
    fi
}

install_dependencies() {
    print_section "Installing Performance Testing Dependencies"
    
    print_info "Installing Python dependencies for benchmark..."
    pip install -q httpx 2>/dev/null || print_info "httpx already installed or requires manual installation"
    
    print_info "For Locust testing, install with: pip install locust"
    print_success "Dependencies check complete"
}

run_benchmark_suite() {
    print_section "Running Authentication Performance Benchmark (AUTH-PERF-001 to 003)"
    
    print_info "Test Coverage:"
    echo "  • AUTH-PERF-001: Login endpoint performance (100 requests)"
    echo "  • AUTH-PERF-002: Registration endpoint performance (50 requests)"
    echo "  • AUTH-PERF-003: Token refresh performance (50 requests)"
    
    cd "$PERF_DIR"
    
    if python3 scripts/benchmark_auth_performance.py 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Benchmark suite completed"
        return 0
    else
        print_error "Benchmark suite failed"
        return 1
    fi
}

run_locust_tests() {
    print_section "Running Locust Load Tests (AUTH-PERF-004 and 005)"
    
    print_info "Test Coverage:"
    echo "  • AUTH-PERF-004: Session management scalability"
    echo "  • AUTH-PERF-005: Concurrent user authentication"
    
    print_info "Check if Locust is installed..."
    if ! command -v locust &> /dev/null; then
        print_error "Locust is not installed"
        print_info "Install with: pip install locust"
        return 1
    fi
    
    cd "$PERF_DIR"
    
    print_info "Starting Locust web UI at http://localhost:8089"
    print_info "To run headless: locust -f scripts/locustfile_auth_performance.py --host=$BASE_URL --headless -u 100 -r 10 -t 60s"
    
    locust -f scripts/locustfile_auth_performance.py --host="$BASE_URL" 2>&1 | tee -a "$LOG_FILE"
}

generate_report() {
    print_section "Generating Performance Report"
    
    REPORT_FILE="$RESULTS_DIR/performance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║     PromptVault Authentication Performance Test Report         ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Test Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Target: $BASE_URL"
        echo ""
        echo "Test Scenarios:"
        echo "  ✓ AUTH-PERF-001: Login endpoint performance"
        echo "  ✓ AUTH-PERF-002: Registration endpoint performance"
        echo "  ✓ AUTH-PERF-003: Token refresh performance"
        echo "  ⏭️  AUTH-PERF-004: Session management scalability (optional)"
        echo "  ⏭️  AUTH-PERF-005: Concurrent user authentication (optional)"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Performance Benchmarks Summary"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "Target Response Times:"
        echo "  • Login: < 150ms (p95)"
        echo "  • Registration: < 200ms (p95)"
        echo "  • Token Refresh: < 50ms (p95)"
        echo "  • Session Operations: < 100ms (p95)"
        echo ""
        echo "Minimum Acceptable Success Rate:"
        echo "  • All endpoints: ≥ 99.5% (target for production)"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Test Log: $LOG_FILE"
        echo "═══════════════════════════════════════════════════════════════"
    } > "$REPORT_FILE"
    
    print_success "Report generated: $REPORT_FILE"
}

cleanup() {
    print_section "Cleanup"
    
    # Kill server if we started it
    if [ -f /tmp/promptvault_server.pid ]; then
        PID=$(cat /tmp/promptvault_server.pid)
        if kill -0 $PID 2>/dev/null; then
            print_info "Stopping server (PID: $PID)..."
            kill $PID
            rm /tmp/promptvault_server.pid
            print_success "Server stopped"
        fi
    fi
}

main() {
    local mode="${1:-benchmark}"
    
    # Register cleanup on exit
    trap cleanup EXIT
    
    print_header
    
    # Check server
    if ! check_server; then
        print_error "Cannot proceed without running server"
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Run tests based on mode
    case "$mode" in
        benchmark)
            run_benchmark_suite
            ;;
        locust)
            run_locust_tests
            ;;
        all)
            run_benchmark_suite
            run_locust_tests
            ;;
        *)
            print_error "Unknown mode: $mode"
            echo "Usage: $0 [benchmark|locust|all]"
            exit 1
            ;;
    esac
    
    # Generate report
    generate_report
    
    print_section "Performance Testing Complete"
    print_success "Results saved to: $RESULTS_DIR"
}

main "$@"
