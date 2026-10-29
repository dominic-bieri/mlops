FROM python:3.15.2-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.15.2-slim AS runtime
# uid 1001 like the GitHub runner, so it can read the mounted Google credentials
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

FROM runtime AS training
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
USER app
ENTRYPOINT ["python", "-m", "sp500_vol.training.train"]

FROM runtime AS features
USER app
ENTRYPOINT ["python", "-m", "sp500_vol.features.pipeline"]
