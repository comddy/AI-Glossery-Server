#!/bin/bash
git stash
git pull --rebase
docker-compose up -d --build