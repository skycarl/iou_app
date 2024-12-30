#!/bin/bash

# Read the .env file line by line
while IFS= read -r line
do
  # Skip lines that are comments or empty
  if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
    # Export the environment variable
    eval export "$line"
  fi
done < .env

echo "Set environment variables from .env"
