#!/bin/bash

# Commands to run in each terminal
commands=(
    "python3 rendezvous_server.py --host 127.0.0.1 --port 33000"
    "python3 nanobot.py --host 127.0.0.1 --port 33001 --marker tumour --name primary"
    "python3 nanobot.py --host 127.0.0.1 --port 33002 --marker acidity --name n1"
    "python3 nanobot.py --host 127.0.0.1 --port 33003 --marker growth --name n2"
    "python3 nanobot.py --host 127.0.0.1 --port 33004 --marker survivin --name n3"
    "python3 nanobot.py --host 127.0.0.1 --port 33005 --marker ecmr --name n4"
    "pkill -f 'tmux attach-session -t python_sessions' && pkill -f 'tmux new-session -d -s python_sessions' && echo 'Session killed in terminal 4'"
    "python3 nanobot.py --host 127.0.0.1 --port 33006 --marker survivin --name n5"
)

# Create a new tmux session
tmux new-session -d -s python_sessions

# Run the commands in each tmux window
for i in {0..7}; do
    tmux new-window -t python_sessions: -n "Terminal $((i+1))" "${commands[i]}; read -p 'Press Enter to exit...'"
done

# Attach to the tmux session
tmux attach-session -t python_sessions