#!/bin/bash

# Check if a tmux session named "my_session" exists, and if not, start a new one
if ! tmux has-session -t my_session -g mouse; then
    tmux new-session -d -s my_session -g mouse
fi

# Create a 2x3 layout with equally spaced panes
tmux split-window -h
tmux split-window -h
tmux split-window -h
tmux split-window -v
tmux select-layout even-horizontal
tmux split-window -v

# Run the server in the leftmost pane
tmux send-keys -t my_session:RVServer "python rendezvous_server.py --host 127.0.0.1 --port 33000" C-m

# Allow some time for the server to start before starting nanobots
sleep 1

# Run nanobots in the remaining panes
tmux send-keys -t my_session:BotA "python3 nanobot.py --host 127.0.0.1 --port 33001 --name botA --marker tumour" C-m
tmux send-keys -t my_session:BotB "python3 nanobot.py --host 127.0.0.1 --port 33002 --name botB --marker acidity" C-m
tmux send-keys -t my_session:BotC "python3 nanobot.py --host 127.0.0.1 --port 33003 --name botC --marker growth" C-m
tmux send-keys -t my_session:BotD "python3 nanobot.py --host 127.0.0.1 --port 33004 --name botD --marker survivin" C-m
tmux send-keys -t my_session:BotE "python3 nanobot.py --host 127.0.0.1 --port 33005 --name botE --marker ecmr" C-m

# Optionally, you can attach to the tmux session
tmux attach-session -t my_session
