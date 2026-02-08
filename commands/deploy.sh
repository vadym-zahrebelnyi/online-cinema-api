#!/bin/bash

set -e

DEPLOY_BRANCH="develop"

handle_error() {
    echo "Error: $1"
    exit 1
}

cd /home/ubuntu/src/online-cinema-api || handle_error "Failed to navigate to the application directory."

echo "Fetching the latest changes from the remote repository..."
git fetch origin $DEPLOY_BRANCH  || handle_error "Failed to fetch updates from the 'origin' remote."

echo "Resetting the local repository to match 'origin/main'..."
git reset --hard origin/$DEPLOY_BRANCH || handle_error "Failed to reset the local repository to 'origin/main'."

echo "Fetching tags from the remote repository..."
git fetch origin --tags || handle_error "Failed to fetch tags from the 'origin' remote."

docker compose -f docker-compose.prod.yml up -d --build || handle_error "Failed to build and run Docker containers using docker-compose.prod.yml."

echo "Deployment completed successfully."
