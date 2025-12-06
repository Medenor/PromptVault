#!/bin/bash
# Pre-Deployment Verification Script for PromptVault
# This script ensures all prerequisites are met before upgrading to a new version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PromptVault Pre-Deployment Checklist${NC}"
echo -e "${BLUE}========================================${NC}\n"

CHECKS_PASSED=0
CHECKS_FAILED=0

# Function to check if Docker is running
check_docker() {
    echo -n "Checking Docker status... "
    if docker-compose ps > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker is running${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗ Docker is not running${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo -n "Checking database connectivity... "
    if docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is accessible${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗ Cannot connect to database${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Function to count records before backup
check_data_volume() {
    echo -n "Checking data volume... "
    PROMPT_COUNT=$(docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;" 2>/dev/null | grep -oE '^[[:space:]]*[0-9]+' | xargs || echo "0")
    if [ "$PROMPT_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $PROMPT_COUNT prompts${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠ No prompts found (may be first deployment)${NC}"
        ((CHECKS_PASSED++))
    fi
}

# Function to verify backup directory
check_backup_dir() {
    echo -n "Checking backup directory... "
    if [ -d "data/backups" ]; then
        echo -e "${GREEN}✓ Backup directory exists${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠ Creating backup directory${NC}"
        mkdir -p data/backups
        ((CHECKS_PASSED++))
    fi
}

# Function to create backup
create_backup() {
    echo -e "\n${BLUE}Creating database backup...${NC}"
    BACKUP_FILE="data/backups/promptvault-pre-deploy-$(date +%Y%m%d_%H%M%S).sql.gz"
    
    if docker-compose exec -T db pg_dump -U promptvault -d promptvault 2>/dev/null | gzip > "$BACKUP_FILE"; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ Backup created: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
        ((CHECKS_PASSED++))
        
        # Verify backup
        echo -n "Verifying backup integrity... "
        if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
            echo -e "${GREEN}✓ Backup verified${NC}"
            ((CHECKS_PASSED++))
        else
            echo -e "${RED}✗ Backup verification failed${NC}"
            ((CHECKS_FAILED++))
            return 1
        fi
    else
        echo -e "${RED}✗ Backup creation failed${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Function to check JWT keys
check_jwt_keys() {
    echo -n "Checking JWT keys... "
    if [ -f "secrets/jwt/private_key.pem" ] && [ -f "secrets/jwt/public_key.pem" ]; then
        echo -e "${GREEN}✓ JWT keys present${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠ JWT keys not found (will be generated on first run)${NC}"
        ((CHECKS_PASSED++))
    fi
}

# Function to check .env file
check_env() {
    echo -n "Checking environment configuration... "
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓ .env file exists${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠ .env file not found${NC}"
        ((CHECKS_PASSED++))
    fi
}

# Function to list recent changes
check_changelog() {
    echo -e "\n${BLUE}Recent changes (from CHANGELOG.md):${NC}"
    if [ -f "docs/CHANGELOG.md" ]; then
        head -30 docs/CHANGELOG.md | grep -E "^#|^-" | head -10
        echo ""
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠ CHANGELOG.md not found${NC}"
        ((CHECKS_PASSED++))
    fi
}

# Main execution
echo -e "${BLUE}Running checks...${NC}\n"

check_docker || exit 1
check_database || exit 1
check_data_volume
check_backup_dir
check_jwt_keys
check_env
check_changelog

echo -e "\n${BLUE}========================================${NC}"
echo -e "Creating backup before deployment..."
echo -e "${BLUE}========================================${NC}\n"

create_backup

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Pre-Deployment Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Checks Passed: $CHECKS_PASSED${NC}"
if [ $CHECKS_FAILED -gt 0 ]; then
    echo -e "${RED}Checks Failed: $CHECKS_FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed! Ready for deployment.${NC}"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review changes in docs/CHANGELOG.md"
echo "2. Run: docker-compose pull"
echo "3. Run: docker-compose up -d web"
echo "4. Monitor: docker-compose logs -f web"
echo "5. If issues, restore from: $(ls -t data/backups/promptvault-pre-deploy-*.sql.gz 2>/dev/null | head -1)"
echo ""
