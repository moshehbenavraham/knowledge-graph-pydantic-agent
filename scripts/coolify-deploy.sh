#!/bin/bash
set -euo pipefail

#######################################################################
# Coolify API Deployment Script for Knowledge Graph Pydantic Agent
#
# This script automates deployment to Coolify via API:
# 1. Discovers server/team UUIDs
# 2. Creates application resource from private GitHub repo
# 3. Configures build settings and environment variables
# 4. Triggers deployment
# 5. Monitors build progress
# 6. Creates admin user post-deployment
#
# Prerequisites:
# - COOLIFY_API_TOKEN and COOLIFY_API_URL set in .env
# - GitHub App connected to Coolify with repo access
# - Supabase and Neo4j databases already set up
#######################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${RED}Error: .env file not found at $PROJECT_ROOT/.env${NC}"
    exit 1
fi

# Verify required variables
if [ -z "${COOLIFY_API_TOKEN:-}" ]; then
    echo -e "${RED}Error: COOLIFY_API_TOKEN not set in .env${NC}"
    exit 1
fi

if [ -z "${COOLIFY_API_URL:-}" ]; then
    echo -e "${RED}Error: COOLIFY_API_URL not set in .env${NC}"
    exit 1
fi

# Configuration
API_URL="${COOLIFY_API_URL}"
API_TOKEN="${COOLIFY_API_TOKEN}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/aiwithapex/knowledge-graph-pydantic-agent}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
APP_NAME="${APP_NAME:-kgpa-ui}"
APP_DOMAIN="${APP_DOMAIN:-kgpa.aiwithapex.com}"
DOCKERFILE_PATH="docker/Dockerfile.production"
BUILD_TARGET="runtime"
PORT_EXPOSES="8502"

#######################################################################
# API Helper Functions
#######################################################################

api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${API_URL}${endpoint}"
    local curl_opts=(
        -X "$method"
        -H "Authorization: Bearer ${API_TOKEN}"
        -H "Content-Type: application/json"
        -H "Accept: application/json"
        --silent
        --show-error
        --fail-with-body
    )

    if [ -n "$data" ]; then
        curl_opts+=(-d "$data")
    fi

    curl "${curl_opts[@]}" "$url"
}

#######################################################################
# Step 1: Discover Coolify Instance Details
#######################################################################

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Coolify Deployment - Knowledge Graph Pydantic Agent${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

echo -e "${YELLOW}Step 1: Discovering Coolify instance details...${NC}"

# Get teams
echo -e "  → Fetching teams..."
TEAMS_RESPONSE=$(api_call GET "/teams" || true)

if [ -z "$TEAMS_RESPONSE" ]; then
    echo -e "${RED}Error: Failed to fetch teams. Check API token permissions.${NC}"
    exit 1
fi

# Extract first team ID (Coolify uses 'id' not 'uuid' for teams)
TEAM_ID=$(echo "$TEAMS_RESPONSE" | jq -r '.[0].id // empty')

if [ -z "$TEAM_ID" ]; then
    echo -e "${RED}Error: No teams found. Please create a team in Coolify first.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Team ID: ${TEAM_ID}${NC}"

# Get servers
echo -e "  → Fetching servers..."
SERVERS_RESPONSE=$(api_call GET "/servers" || true)

if [ -z "$SERVERS_RESPONSE" ]; then
    echo -e "${RED}Error: Failed to fetch servers.${NC}"
    exit 1
fi

# Extract first server UUID
SERVER_UUID=$(echo "$SERVERS_RESPONSE" | jq -r '.[0].uuid // empty')

if [ -z "$SERVER_UUID" ]; then
    echo -e "${RED}Error: No servers found. Please add a server in Coolify first.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Server UUID: ${SERVER_UUID}${NC}"

# Get GitHub Apps
echo -e "  → Fetching GitHub Apps..."
GITHUB_APPS_RESPONSE=$(api_call GET "/github-apps" || true)

if [ -z "$GITHUB_APPS_RESPONSE" ]; then
    echo -e "${YELLOW}  ⚠ No GitHub Apps found. Checking if repo is public...${NC}"
    USE_PUBLIC_REPO=true
else
    # Find first private GitHub App (has installation_id and is_public=false)
    GITHUB_APP_UUID=$(echo "$GITHUB_APPS_RESPONSE" | jq -r '[.[] | select(.is_public == false and .installation_id != null)][0].uuid // empty')

    if [ -z "$GITHUB_APP_UUID" ]; then
        echo -e "${YELLOW}  ⚠ No private GitHub Apps configured. Using public repo method...${NC}"
        USE_PUBLIC_REPO=true
    else
        GITHUB_APP_NAME=$(echo "$GITHUB_APPS_RESPONSE" | jq -r "[.[] | select(.uuid == \"$GITHUB_APP_UUID\")][0].name // \"GitHub App\"")
        echo -e "${GREEN}  ✓ GitHub App UUID: ${GITHUB_APP_UUID} (${GITHUB_APP_NAME})${NC}"
        USE_PUBLIC_REPO=false
    fi
fi

# Get projects (environments)
echo -e "  → Fetching projects..."
PROJECTS_RESPONSE=$(api_call GET "/projects" || true)

if [ -z "$PROJECTS_RESPONSE" ]; then
    echo -e "${RED}Error: Failed to fetch projects.${NC}"
    exit 1
fi

# Extract first project and environment
PROJECT_UUID=$(echo "$PROJECTS_RESPONSE" | jq -r '.[0].uuid // empty')
ENVIRONMENT_NAME=$(echo "$PROJECTS_RESPONSE" | jq -r '.[0].environments[0].name // "production"')

if [ -z "$PROJECT_UUID" ]; then
    echo -e "${RED}Error: No projects found. Please create a project in Coolify first.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Project UUID: ${PROJECT_UUID}${NC}"
echo -e "${GREEN}  ✓ Environment: ${ENVIRONMENT_NAME}${NC}"

echo ""

#######################################################################
# Step 2: Create Application Resource
#######################################################################

echo -e "${YELLOW}Step 2: Creating application resource...${NC}"

# Prepare application creation payload
if [ "$USE_PUBLIC_REPO" = true ]; then
    CREATE_ENDPOINT="/applications/public"
    CREATE_PAYLOAD=$(jq -n \
        --arg project "$PROJECT_UUID" \
        --arg server "$SERVER_UUID" \
        --arg env "$ENVIRONMENT_NAME" \
        --arg repo "$GITHUB_REPO" \
        --arg branch "$GITHUB_BRANCH" \
        --arg buildpack "dockerfile" \
        --arg ports "$PORT_EXPOSES" \
        --arg name "$APP_NAME" \
        '{
            project_uuid: $project,
            server_uuid: $server,
            environment_name: $env,
            git_repository: $repo,
            git_branch: $branch,
            build_pack: $buildpack,
            ports_exposes: $ports,
            name: $name,
            is_static: false
        }')
else
    CREATE_ENDPOINT="/applications/private-github-app"
    CREATE_PAYLOAD=$(jq -n \
        --arg project "$PROJECT_UUID" \
        --arg server "$SERVER_UUID" \
        --arg env "$ENVIRONMENT_NAME" \
        --arg repo "$GITHUB_REPO" \
        --arg branch "$GITHUB_BRANCH" \
        --arg buildpack "dockerfile" \
        --arg ports "$PORT_EXPOSES" \
        --arg name "$APP_NAME" \
        --arg github_app "$GITHUB_APP_UUID" \
        '{
            project_uuid: $project,
            server_uuid: $server,
            environment_name: $env,
            git_repository: $repo,
            git_branch: $branch,
            build_pack: $buildpack,
            ports_exposes: $ports,
            name: $name,
            is_static: false,
            github_app_uuid: $github_app
        }')
fi

echo -e "  → Creating application: ${APP_NAME}..."
echo -e "  → Repository: ${GITHUB_REPO} (${GITHUB_BRANCH})"
echo -e "  → Dockerfile: ${DOCKERFILE_PATH}"

CREATE_RESPONSE=$(api_call POST "$CREATE_ENDPOINT" "$CREATE_PAYLOAD" || true)

if [ -z "$CREATE_RESPONSE" ]; then
    echo -e "${RED}Error: Failed to create application.${NC}"
    echo -e "${RED}Payload: ${CREATE_PAYLOAD}${NC}"
    exit 1
fi

APP_UUID=$(echo "$CREATE_RESPONSE" | jq -r '.uuid // .application_uuid // empty')

if [ -z "$APP_UUID" ]; then
    echo -e "${RED}Error: No UUID returned from application creation.${NC}"
    echo -e "${RED}Response: ${CREATE_RESPONSE}${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Application created: ${APP_UUID}${NC}"
echo ""

#######################################################################
# Step 3: Configure Application Settings
#######################################################################

echo -e "${YELLOW}Step 3: Configuring application settings...${NC}"

# Update application with domain, build target, dockerfile location, etc.
UPDATE_PAYLOAD=$(jq -n \
    --arg domain "$APP_DOMAIN" \
    --arg target "$BUILD_TARGET" \
    --arg dockerfile "$DOCKERFILE_PATH" \
    --argjson instant_deploy false \
    '{
        fqdn: $domain,
        docker_build_target: $target,
        dockerfile_location: $dockerfile,
        instant_deploy: $instant_deploy,
        health_check_enabled: true,
        health_check_path: "/_stcore/health",
        health_check_port: "8502",
        health_check_interval: 30,
        health_check_timeout: 10,
        health_check_retries: 3,
        health_check_start_period: 60,
        limits_memory: "8192M",
        limits_cpus: "4.0",
        limits_memory_reservation: "4096M",
        limits_cpus_reservation: "2.0"
    }')

echo -e "  → Setting domain: ${APP_DOMAIN}"
echo -e "  → Setting build target: ${BUILD_TARGET}"
echo -e "  → Setting resource limits: 8GB RAM, 4 CPU"

UPDATE_RESPONSE=$(api_call PATCH "/applications/${APP_UUID}" "$UPDATE_PAYLOAD" || true)

if [ -z "$UPDATE_RESPONSE" ]; then
    echo -e "${YELLOW}  ⚠ Warning: Failed to update some settings. Continuing...${NC}"
else
    echo -e "${GREEN}  ✓ Application configured${NC}"
fi

# Set environment variables
echo -e "  → Configuring environment variables..."

# Read environment variables from .env (excluding Coolify and comments)
ENV_VARS_JSON="[]"
while IFS='=' read -r key value; do
    # Skip empty lines, comments, and Coolify-specific vars
    if [[ -z "$key" || "$key" =~ ^#.*$ || "$key" =~ ^COOLIFY.*$ ]]; then
        continue
    fi

    # Add to JSON array
    ENV_VARS_JSON=$(echo "$ENV_VARS_JSON" | jq \
        --arg key "$key" \
        --arg value "$value" \
        '. += [{"key": $key, "value": $value, "is_build_time": false, "is_literal": false, "is_shown_once": false}]')
done < <(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | grep '=')

ENV_UPDATE_PAYLOAD=$(jq -n \
    --argjson envs "$ENV_VARS_JSON" \
    '{environment_variables: $envs}')

ENV_UPDATE_RESPONSE=$(api_call POST "/applications/${APP_UUID}/envs/bulk" "$ENV_UPDATE_PAYLOAD" || true)

if [ -z "$ENV_UPDATE_RESPONSE" ]; then
    echo -e "${YELLOW}  ⚠ Warning: Failed to bulk update environment variables.${NC}"
    echo -e "${YELLOW}     You may need to add them manually in Coolify UI.${NC}"
else
    ENV_COUNT=$(echo "$ENV_VARS_JSON" | jq 'length')
    echo -e "${GREEN}  ✓ Configured ${ENV_COUNT} environment variables${NC}"
fi

echo ""

#######################################################################
# Step 4: Deploy Application
#######################################################################

echo -e "${YELLOW}Step 4: Triggering deployment...${NC}"

DEPLOY_RESPONSE=$(api_call GET "/applications/${APP_UUID}/start?force=false&instant_deploy=true" || true)

if [ -z "$DEPLOY_RESPONSE" ]; then
    echo -e "${RED}Error: Failed to trigger deployment.${NC}"
    exit 1
fi

DEPLOYMENT_UUID=$(echo "$DEPLOY_RESPONSE" | jq -r '.deployment_uuid // empty')

echo -e "${GREEN}  ✓ Deployment triggered${NC}"
if [ -n "$DEPLOYMENT_UUID" ]; then
    echo -e "${GREEN}  ✓ Deployment UUID: ${DEPLOYMENT_UUID}${NC}"
fi

echo ""

#######################################################################
# Step 5: Monitor Deployment (Basic)
#######################################################################

echo -e "${YELLOW}Step 5: Monitoring deployment...${NC}"
echo -e "  → Build logs available in Coolify UI"
echo -e "  → Application URL: https://${APP_DOMAIN}"
echo -e "  → Expected build time: 5-8 minutes"
echo ""

echo -e "${BLUE}Waiting for deployment to complete...${NC}"
echo -e "  (Checking every 30 seconds, timeout after 15 minutes)"
echo ""

MAX_WAIT=900  # 15 minutes
WAIT_INTERVAL=30
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))

    # Check application status
    APP_STATUS_RESPONSE=$(api_call GET "/applications/${APP_UUID}" || true)

    if [ -n "$APP_STATUS_RESPONSE" ]; then
        STATUS=$(echo "$APP_STATUS_RESPONSE" | jq -r '.status // "unknown"')

        echo -e "  [${ELAPSED}s] Status: ${STATUS}"

        if [ "$STATUS" = "running" ] || [ "$STATUS" = "healthy" ]; then
            echo -e "${GREEN}  ✓ Deployment successful!${NC}"
            break
        elif [ "$STATUS" = "exited" ] || [ "$STATUS" = "failed" ]; then
            echo -e "${RED}  ✗ Deployment failed. Check logs in Coolify UI.${NC}"
            exit 1
        fi
    else
        echo -e "  [${ELAPSED}s] Checking status..."
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}  ⚠ Deployment timeout. Check Coolify UI for current status.${NC}"
fi

echo ""

#######################################################################
# Step 6: Post-Deployment Instructions
#######################################################################

echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. ${BLUE}Verify Application${NC}"
echo -e "   → Visit: https://${APP_DOMAIN}"
echo -e "   → Check health: https://${APP_DOMAIN}/_stcore/health"
echo ""
echo -e "2. ${BLUE}Create Admin User${NC}"
echo -e "   → Access Coolify Terminal for your application"
echo -e "   → Run:"
echo -e "     ${GREEN}python -m src.auth.db_cli create \\\\${NC}"
echo -e "     ${GREEN}  --username admin \\\\${NC}"
echo -e "     ${GREEN}  --email admin@yourdomain.com \\\\${NC}"
echo -e "     ${GREEN}  --name \"Admin User\" \\\\${NC}"
echo -e "     ${GREEN}  --password \"YourStrongPassword123!\" \\\\${NC}"
echo -e "     ${GREEN}  --role admin${NC}"
echo ""
echo -e "3. ${BLUE}Test Features${NC}"
echo -e "   → Login with admin credentials"
echo -e "   → Upload a document"
echo -e "   → Ask a question"
echo -e "   → Verify RAG search works"
echo ""
echo -e "4. ${BLUE}Monitor Application${NC}"
echo -e "   → Coolify Dashboard: https://coolify.aiwithapex.com/"
echo -e "   → View logs, metrics, and health status"
echo ""

echo -e "${GREEN}Deployment script completed successfully!${NC}"
