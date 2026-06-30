# Hugging Face Space (Docker SDK) — runs the Lara connector on port 7860.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Public/demo defaults. SESSION_SIGNING_SECRET is injected as a Space SECRET (not here).
ENV HOST=0.0.0.0 \
    PORT=7860 \
    LARA_TRANSPORT=http \
    AUTH_DISABLED=1 \
    GATING_ENABLED=false \
    PUBLIC_TIER=max \
    LARA_DB_PATH=/tmp/lara.db

EXPOSE 7860

CMD ["python", "server.py"]
