#!/bin/bash
set -e

# Function to check if MongoDB is available
function mongodb_ready(){
    nc -z mongo 27017
    if [[ $? -ne 0 ]]; then
        echo "MongoDB is not available, waiting..."
        return 1
    fi
    echo "MongoDB is available, proceeding..."
    return 0
}

# Wait for MongoDB to be available
until mongodb_ready; do
    sleep 2
done

# Run the main command
exec "$@"