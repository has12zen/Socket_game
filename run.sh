#!/bin/bash

clear

current_directory="$(pwd)"

daphne -e ssl:8443:privateKey="$current_directory/certs/server.key":certKey="$current_directory/certs/server.crt" ChatApp.asgi:application -p 8000 -b 0.0.0.0
