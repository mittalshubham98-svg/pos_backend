#!/bin/sh
set -e

# If a persistent volume is mounted at /data (this is where the Railway deploy guide in
# README.md tells you to attach one), keep item images there instead of the container's
# ephemeral filesystem so they survive redeploys and restarts. Point DATABASE_URL at a
# path under /data too (set as an env var on the host) for the same reason with the
# SQLite file itself.
if [ -d /data ]; then
    mkdir -p /data/images
    rm -rf /app/app/static/images
    ln -s /data/images /app/app/static/images
fi

# Railway (and most PaaS Docker runners) assign a dynamic port via $PORT at runtime
# rather than honoring a fixed EXPOSE/CMD port, so bind to it directly instead of the
# Dockerfile's default of 8000 (kept as a fallback for plain `docker run`).
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
