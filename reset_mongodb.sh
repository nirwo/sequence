#!/bin/bash

echo "Stopping containers..."
docker-compose down

echo "Removing MongoDB volume..."
docker volume rm app-monitor_mongodb_data

echo "Removing any leftover MongoDB files..."
sudo rm -rf ./mongodb/data/*

echo "Starting containers fresh..."
docker-compose up -d

echo "Waiting for MongoDB to be ready..."
sleep 5

echo "Running database initialization..."
python3 init_db.py

echo "MongoDB has been reset and reinitialized!"
