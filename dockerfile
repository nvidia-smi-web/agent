FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV NVIDIA_VISIBLE_DEVICES=all \
	NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /app

RUN apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget tzdata && \
	rm -rf /var/lib/apt/lists/*

RUN wget -qO- https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

RUN uv python install 3.12

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache-dir

COPY . .

CMD [".venv/bin/python", "main.py"]
