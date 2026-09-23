FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.12.16 /uv /usr/local/bin/uv

WORKDIR /app

# Exact versions with hashes: a package re-published with malicious code will not install.
# After changing pyproject.toml: uv pip compile pyproject.toml --generate-hashes --python-version 3.13 -o requirements.lock
COPY pyproject.toml requirements.lock ./
RUN uv pip install --system --no-cache --require-hashes -r requirements.lock

COPY . .

# the photos volume is mounted here; a named volume starts with this folder's owner, so create it first
RUN useradd --create-home --uid 1000 app && mkdir -p /app/media && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
