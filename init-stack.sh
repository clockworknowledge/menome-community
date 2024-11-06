#!/bin/bash

# Initialize Neo4j and MinIO buckets
docker compose exec -T api-dev python /menome/init_stack.py "$@"

# Set up MinIO access

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    while IFS='=' read -r key value; do
        # Ensure that key-value pairs are properly formatted
        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            export "$key=$value"
        fi
    done < .env
fi

# Configuration from .env file
MINIO_ALIAS=minio-dev
MINIO_CONTAINER=minio-dev
MINIO_ENDPOINT=${MINIO_ENDPOINT:-http://localhost:9000}
ROOT_ACCESS_KEY=${MINIO_ROOT_USER}
ROOT_SECRET_KEY=${MINIO_ROOT_PASSWORD}
NEW_ACCESS_KEY=${MINIO_ACCESS_KEY}
NEW_SECRET_KEY=${MINIO_SECRET_KEY}
USER_POLICY=${USER_POLICY:-readwrite}

# Check if mc is already configured for the alias
docker exec -it "$MINIO_CONTAINER" mc alias list | grep -q "$MINIO_ALIAS"
if [ $? -ne 0 ]; then
  # Configure mc alias for MinIO server
  docker exec -it "$MINIO_CONTAINER" mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$ROOT_ACCESS_KEY" "$ROOT_SECRET_KEY"
  echo "Configured mc alias for MinIO"
else
  echo "mc alias already configured for MinIO"
fi

# Create the new user
docker exec -it "$MINIO_CONTAINER" mc admin user add "$MINIO_ALIAS" "$NEW_ACCESS_KEY" "$NEW_SECRET_KEY"
echo "Created new user with access key: $NEW_ACCESS_KEY"

# Attach policy to the user
docker exec -it "$MINIO_CONTAINER" mc admin policy attach "$MINIO_ALIAS" "$USER_POLICY" --user "$NEW_ACCESS_KEY"
echo "Policy '$USER_POLICY' applied to user: $NEW_ACCESS_KEY"

# Create necessary buckets
docker exec -it "$MINIO_CONTAINER" mc mb "$MINIO_ALIAS/notes" 2>/dev/null || echo "Bucket 'notes' already exists"
docker exec -it "$MINIO_CONTAINER" mc mb "$MINIO_ALIAS/files" 2>/dev/null || echo "Bucket 'files' already exists"
echo "Created or verified buckets 'notes' and 'files'"

exit $?
