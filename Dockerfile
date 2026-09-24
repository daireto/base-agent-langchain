FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy \
	PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
	&& apt-get install --no-install-recommends -y libgomp1 \
	&& rm -rf /var/lib/apt/lists/* \
	&& python -m pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY data ./data

ENV PRESENTATION_MODE=api

CMD ["uv", "run", "--no-dev", "src/main.py"]
