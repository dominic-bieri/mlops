FROM python:3.15.2-slim AS uv
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./

FROM uv AS builder
RUN uv sync --locked --no-default-groups --no-install-project
COPY src ./src
RUN uv sync --locked --no-default-groups --no-editable

FROM builder AS api-builder
RUN uv sync --locked --no-default-groups --group api --no-editable

FROM uv AS ui-builder
RUN uv sync --locked --only-group ui

FROM python:3.15.2-slim AS runtime
# uid 1001 like the GitHub runner, so it can read the mounted Google credentials
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --no-create-home app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

FROM runtime AS lightgbm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM lightgbm AS training
COPY --from=builder --chown=app:app /app/.venv /app/.venv
USER app
ENTRYPOINT ["python", "-m", "sp500_vol.training.train"]

FROM lightgbm AS inference
COPY --from=api-builder --chown=app:app /app/.venv /app/.venv
ARG GITHUB_SHA=local
ENV GITHUB_SHA=$GITHUB_SHA
USER app
ENTRYPOINT ["uvicorn", "sp500_vol.inference.api:app", "--host", "0.0.0.0", "--port", "8080"]

FROM runtime AS ui
COPY --from=ui-builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app ui ./ui
COPY --chown=app:app .streamlit ./.streamlit
USER app
ENTRYPOINT ["streamlit", "run", "ui/app.py", "--server.port=8080", "--server.address=0.0.0.0", \
    "--server.headless=true"]

FROM runtime AS features
COPY --from=builder --chown=app:app /app/.venv /app/.venv
USER app
ENTRYPOINT ["python", "-m", "sp500_vol.features.pipeline"]
