# VeloTimer

VeloTimer is a cycling training stopwatch system built for athletes and coaches. It combines a Raspberry Pi-based timing interface, a local web controller, and a cloud-backed athlete portal for reviewing sessions, tracking laps, and managing training data.

## Overview

This repository contains:

- a stopwatch interface for a Raspberry Pi,
- a local Flask bridge for communicating with the Pi and browser,
- a FastAPI backend for storing and retrieving training data,
- a polished athlete portal for authentication, profile management, dashboard stats, and manual entries.

## Features

- Start and stop a cycling session from the Pi/web interface
- Record lap times and total session duration
- Display live timer state in the browser
- Upload completed sessions to a backend service
- View athlete dashboards with session summaries and lap trends
- Register/login through the athlete portal
- Add manual training entries and delete sessions

## Project Structure

- [fastapi_backend.py](fastapi_backend.py) — FastAPI backend with authentication, athlete data, and trial/session storage
- [serve.py](serve.py) — Flask server that bridges the browser UI, Pi hardware, and backend
- [pi_stopwatch.py](pi_stopwatch.py) — Raspberry Pi stopwatch logic with button input, buzzer, and display output
- [velotimer.html](velotimer.html) — Browser-based timer UI used during live sessions
- [athlete_portal.html](athlete_portal.html) — Athlete dashboard and portal UI
- [start.sh](start.sh) — Raspberry Pi startup script for launching the kiosk workflow

## How It Works

1. The timer UI opens in the browser and lets the user choose an athlete.
2. The local Flask service relays timer state to and from the Raspberry Pi process.
3. The Pi script runs the stopwatch loop, records laps, and uploads session data to the backend.
4. The athlete portal connects to the backend to show training history, profile data, and analytics.

## Requirements

### Python packages

Install the core requirements:

```bash
pip install fastapi uvicorn flask requests psycopg2-binary
```

If you are running the Pi hardware workflow, also install the Pi-specific packages used by the stopwatch script:

```bash
pip install gpiozero tm1637
```

### Backend database

The FastAPI service expects a PostgreSQL database and uses the following data model concepts:

- athletes
- users
- trials

The code attempts to create the users table automatically, but the rest of the schema should be present in your database environment.

## Quick Start

### 1. Start the backend

Run the FastAPI server:

```bash
uvicorn fastapi_backend:app --host 0.0.0.0 --port 8000
```

### 2. Start the local bridge

In another terminal:

```bash
python serve.py
```

This serves the timer UI at:

- http://localhost:3000

### 3. Open the timer UI

Open the browser to:

- http://localhost:3000

### 4. Open the athlete portal

If the backend is running locally, open:

- http://localhost:8000/portal

## Raspberry Pi Usage

For a Raspberry Pi deployment, the expected startup flow is:

```bash
bash start.sh
```

This script:

- starts the local Flask bridge,
- launches the browser in kiosk mode,
- runs the Pi stopwatch process.

## Notes

- The project currently uses hard-coded service URLs and backend credentials in several places. If you want to use your own deployment, update those values before going live.
- The FastAPI app uses token-based authentication for protected routes.
- The Pi-side script communicates with the Flask bridge over HTTP endpoints.

## Future Improvements

Possible enhancements include:

- moving configuration to environment variables,
- adding Docker support,
- improving database schema management,
- securing API credentials and CORS behavior,
- adding test coverage for the backend endpoints.
