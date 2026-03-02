#!/bin/bash
# Start the ARQ background worker in the background (&)
arq app.worker.WorkerSettings &

# Start the FastAPI server on the port Render assigns
uvicorn app.main:app --host 0.0.0.0 --port $PORT