FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb')); deps=p['project']['dependencies'] + p['project']['optional-dependencies']['ml']; open('/tmp/requirements.txt','w',encoding='utf-8').write('\n'.join(deps))" \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "torch>=2.3.1"

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
