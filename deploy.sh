#!/bin/bash

set -e

# Configuration
log_file="deploy.log"
max_wait_time=120
health_check_retries=12
health_check_interval=10

# Setup simple logging
log() {
    local message="$(date '+%Y-%m-%d %H:%M:%S') $1"
    echo "$message"
    echo "$message" >> $log_file
}

log "Starting deployment process..."

# Function to check disk space (Pi has limited space)
check_disk_space() {
    available_space=$(df . | awk 'NR==2 {print $4}')
    required_space=1048576  # 1GB in KB
    if [ "$available_space" -lt "$required_space" ]; then
        echo "Warning: Low disk space. Available: ${available_space}KB, Recommended: ${required_space}KB"
        echo "Running Docker cleanup..."
        docker system prune -f || echo "Docker cleanup failed, continuing anyway"
    fi
}

# Function to wait for container health
wait_for_health() {
    local container_name=$1
    local retries=$health_check_retries

    echo "Waiting for $container_name to be healthy..."
    while [ $retries -gt 0 ]; do
        if docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
            echo "$container_name is healthy"
            return 0
        fi
        echo "Waiting for $container_name health check... ($retries retries left)"
        sleep $health_check_interval
        retries=$((retries - 1))
    done

    echo "ERROR: $container_name failed health check"
    return 1
}

# Function to rollback on failure
rollback() {
    echo "ROLLBACK: Attempting to restore previous state..."
    if [ -n "$previous_commit" ]; then
        git reset --hard "$previous_commit" || echo "Git rollback failed"
    fi
    docker compose -f docker-compose.yml down || echo "Failed to stop containers during rollback"
    docker compose -f docker-compose.yml up -d || echo "Failed to restart containers during rollback"
    echo "Rollback attempt completed"
    exit 1
}

# Trap to handle failures
trap rollback ERR

echo "Checking disk space..."
check_disk_space

echo "Saving current git commit for potential rollback..."
previous_commit=$(git rev-parse HEAD)
echo "Previous commit: $previous_commit"

echo "Pulling from git..."
if ! timeout 60 git pull git@github.com:skycarl/iou_app.git; then
    echo "Failed to pull from git (timeout or error)"
    exit 1
fi

current_commit=$(git rev-parse HEAD)
echo "Current commit: $current_commit"

if [ "$previous_commit" = "$current_commit" ]; then
    echo "No new changes detected, but continuing with restart..."
fi

echo "Stopping Docker containers gracefully..."
if ! timeout 30 docker compose -f docker-compose.yml down; then
    echo "Failed to stop Docker containers gracefully, forcing stop..."
    docker compose -f docker-compose.yml kill || echo "Force kill failed"
    docker compose -f docker-compose.yml rm -f || echo "Container removal failed"
fi

echo "Building and starting Docker containers..."
if ! timeout $max_wait_time docker compose -f docker-compose.yml up -d --build; then
    echo "Failed to start Docker containers"
    rollback
fi

echo "Verifying container health..."
if ! wait_for_health "iou_app"; then
    echo "App container health check failed"
    docker logs iou_app --tail 50
    rollback
fi

# Optional: Check if bot container exists and wait for it too
if docker ps --format '{{.Names}}' | grep -q "iou_bot"; then
    echo "Bot container detected, checking status..."
    # Bot might not have health checks, so just verify it's running
    if ! docker ps --format '{{.Names}}' | grep -q "iou_bot"; then
        echo "Warning: Bot container is not running"
        docker logs iou_bot --tail 20
    else
        echo "Bot container is running"
    fi
fi

echo "Cleaning up old Docker images to save space..."
docker image prune -f || echo "Image cleanup failed, continuing anyway"

# Disable trap since we succeeded
trap - ERR

log "Deployment completed successfully!"
log "App is running at: http://localhost:8000"
log "Health check: http://localhost:8000/healthcheck"

# Final verification
log "Final status check:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Brief pause to ensure all output is flushed
sleep 1

log "Script completed successfully"

# Ensure script exits cleanly
exit 0
