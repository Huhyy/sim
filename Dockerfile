FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    API_DOCS_ENABLED=false \
    COOKIE_SECURE=true \
    HOME=/tmp

WORKDIR /app

RUN groupadd --system --gid 10001 simulator \
    && useradd --system --uid 10001 --gid simulator --no-create-home simulator

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY sim_app ./sim_app

USER 10001:10001

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn sim_app.api.app:app --host 0.0.0.0 --port \"${PORT:-8080}\" --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
