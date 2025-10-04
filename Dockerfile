FROM python:3.12.5-slim-bookworm

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && pip install pipenv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /vagabond

COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --ignore-pipfile

COPY . .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]