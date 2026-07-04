# syntax=docker/dockerfile:1

ARG VARIANT="3.13"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

ENV DEBIAN_FRONTEND=noninteractive

# Install compilation tooling and system libraries needed for common wheels

# This suppresses the warning about pinning apt-get package versions,
# which is often unnecessary in dev containers where you want the latest stable versions.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    curl \
    git \
    shellcheck \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install hadolint for local pre-commit parity across architectures.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "${arch}" in \
      amd64) asset="hadolint-Linux-x86_64" ;; \
      arm64) asset="hadolint-Linux-arm64" ;; \
      *) echo "Unsupported architecture for hadolint: ${arch}" >&2; exit 2 ;; \
    esac; \
    curl -fsSL -o /usr/local/bin/hadolint \
      "https://github.com/hadolint/hadolint/releases/download/v2.12.0/${asset}"; \
    chmod +x /usr/local/bin/hadolint

# Install uv globally for fast dependency management
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# Ensure uv creates in-project virtual environments by default
ENV UV_PROJECT_ENVIRONMENT=.venv
ENV UV_LINK_MODE=copy

# Prefer the in-container venv Python in PATH for new shells (will be created in postCreate)
ENV PATH="/home/vscode/.venv/bin:${PATH}"

# Ensure matplotlib can cache without permission issues when running as vscode user
RUN mkdir -p /home/vscode/.cache/matplotlib && chown -R vscode:vscode /home/vscode/.cache
