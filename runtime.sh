#!/bin/bash

# Define the log file
LOG_FILE="$HOME/logfile.log"

# Log date and time
echo "Script run at: $(date)" | tee -a "$LOG_FILE"

# First curl command
curl -s --location --request POST 'https://localhost:5000/v1/api/sso/validate' -k 2>&1 | tee -a "$LOG_FILE"

# Wait for 5 seconds
sleep 5

# Second curl command
curl -s --location --request POST 'https://localhost:5000/v1/api/iserver/reauthenticate' --header 'accept: application/json' -k 2>&1 | tee -a "$LOG_FILE"

# Wait for 1 second
sleep 1

# Third curl command
curl -s -X 'POST' -k 'https://localhost:5000/v1/api/tickle' -H 'accept: application/json' -d '' 2>&1 | tee -a "$LOG_FILE"
