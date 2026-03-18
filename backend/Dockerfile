ARG PYTHON_BASE_IMAGE=python:3.10-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

ARG APT_MIRROR=

# Runtime dependencies for image/audio processing and TTS handling.
RUN set -eux; \
    if [ -n "${APT_MIRROR:-}" ]; then \
        mirror="${APT_MIRROR%/}"; \
        if [ -f /etc/apt/sources.list ]; then \
            sed -i "s|http://deb.debian.org/debian|${mirror}/debian|g; s|https://deb.debian.org/debian|${mirror}/debian|g; s|http://security.debian.org/debian-security|${mirror}/debian-security|g; s|https://security.debian.org/debian-security|${mirror}/debian-security|g" /etc/apt/sources.list; \
        fi; \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
            sed -i "s|http://deb.debian.org/debian|${mirror}/debian|g; s|https://deb.debian.org/debian|${mirror}/debian|g; s|http://security.debian.org/debian-security|${mirror}/debian-security|g; s|https://security.debian.org/debian-security|${mirror}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
        fi; \
    fi; \
    apt-get update -o Acquire::Retries=5 -o Acquire::http::Timeout=30; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        curl \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt /app/
# Player image keeps dependencies lean and avoids pulling large CUDA wheels.
RUN pip install --upgrade pip && \
    grep -v "^sentence-transformers" requirements.txt > requirements.docker.txt && \
    pip install -r requirements.docker.txt -c constraints.txt

COPY . /app

RUN mkdir -p \
    /app/audio/cache \
    /app/vector_db \
    /app/images/characters \
    /app/images/scenes \
    /app/images/smallscenes \
    /app/images/composite

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
