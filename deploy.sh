#!/bin/bash

set -e

log_file="deploy.log"
exec > >(tee -i $log_file)
exec 2>&1

echo "Pulling from git"
if ! git pull git@github.com:skycarl/iou_app.git; then
  echo "Failed to pull from git"
  exit 1
fi

echo "Pulling Docker images"
if ! docker pull ghcr.io/skycarl/iou_app:latest; then
  echo "Failed to pull iou_app image"
  exit 1
fi

echo "Restarting Docker containers"
if ! docker compose -f docker-compose.yml down; then
  echo "Failed to stop Docker containers"
  exit 1
fi

if ! docker compose -f docker-compose.yml up -d; then
  echo "Failed to start Docker containers"
  exit 1
fi

echo "Deployment completed successfully"
