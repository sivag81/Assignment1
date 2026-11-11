# book-service

Independent FastAPI service for the Online Bookstore assignment.

## Configuration and startup

Set DATABASE_URL to a PostgreSQL SQLAlchemy URL (postgresql+psycopg://...).
Apply init.sql to an empty service database before running the API.
For order-service, set BOOK_SERVICE_URL to the Book API root URL.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

GET /docs shows the API contracts. GET /health checks liveness; GET /ready
checks access to the service table. See the parent RUN_GUIDE.md for Compose
and Minikube execution. Keep this directory in its own GitHub repository.

## Docker build

```bash
docker build -t book-service:1.0 .
```

Run isolated unit tests from the parent bookstore directory with
`python3 -m unittest discover -s tests -v` after installing requirements.
The suite tests both services using SQLite; PostgreSQL integration is checked
by the smoke test against the running containers.
