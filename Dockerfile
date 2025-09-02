# FROM debian:trixie-20250811-slim as install
FROM python:3.13.7-slim-trixie as install

RUN apt-get update && apt-get install -y --no-install-recommends pipx git && rm -rf /var/lib/apt/lists/*
RUN pipx install uv
ENV PATH="/root/.local/bin:${PATH}"
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
COPY pyproject.toml uv.lock feedmixer_api.py feedmixer_wsgi.py feedmixer.py /app/

WORKDIR /app/
RUN uv venv && \
    uv sync && \
    uv pip install gunicorn

# build layer without git, pipx, or uv
FROM python:3.13.7-slim-trixie
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

copy --from=install /app/ /app

RUN chown -R nobody /app/
WORKDIR /app/

ENV PATH="/app/.venv/bin/:$PATH"
USER nobody
ENTRYPOINT ["gunicorn"]
CMD ["-b", ":8000", "feedmixer_wsgi"]
