#!/bin/bash
cd /opt/AI-Glossery-Server
git pull --rebase
docker-compose up -d --build