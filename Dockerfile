FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /uvx /bin/

# O ambiente fica fora de /app para não ser escondido pelo volume do compose.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependências antes do código, para aproveitar o cache de camadas.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
