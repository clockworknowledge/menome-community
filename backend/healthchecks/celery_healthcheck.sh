#!/bin/bash

# Log the start of the health check
echo "$(date): Starting Celery worker health check."

# Check if the Celery worker process is running
if pgrep -f "celery worker" > /dev/null; then
    echo "$(date): Celery worker is healthy."
    exit 0
else
    echo "$(date): Celery worker is unhealthy."
    exit 1
fi
