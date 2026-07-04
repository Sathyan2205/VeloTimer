#!/bin/bash

# Keep trying forever until Pi is turned off
while true; do
    echo "Starting VeloTimer session..."

    cd /home/hashlog

    # Kill any old instances
    pkill -f serve.py
    pkill -f chromium
    sleep 2

    # Start serve.py in background
    python3 serve.py &
    SERVE_PID=$!
    sleep 3

    # Open Chromium in kiosk mode
    chromium --kiosk --disable-infobars http://localhost:3000 &
    CHROMIUM_PID=$!
    sleep 5

    # Run pi_code.py — this runs the full session loop
    # When pi_code.py exits for any reason, the while loop restarts everything
    DISPLAY=:0 python3 pi_code.py

    echo "pi_code.py exited. Restarting everything in 3 seconds..."

    # Clean up before restarting
    kill $SERVE_PID 2>/dev/null
    kill $CHROMIUM_PID 2>/dev/null
    pkill -f serve.py
    pkill -f chromium
    sleep 3

done
