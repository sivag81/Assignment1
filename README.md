# Online Bookstore

An assignment demonstration with independent Python FastAPI Book and Order services. Each service uses its own PostgreSQL database. The Order service calls the Book service to validate a book and calculate the order total.

## Files

- `book-service/`: Python API, Dockerfile, requirements and SQL schema.
- `order-service/`: Python API, Dockerfile, requirements and SQL schema.
- `deployment/compose.yaml`: both APIs and both PostgreSQL containers.
- `deployment/k8s/`: Kubernetes deployment resources.
- `tests/`: isolated service tests.
- `smoke_test.py`: verification against running APIs.
- `Bookstore.postman_collection.json`: demo requests and response checks.
- `RUN_GUIDE.md`: Rancher Desktop and Minikube instructions.

## Run with Rancher Desktop

Select **dockerd (Moby)** in Rancher Desktop, then run from this repository:

```bash
docker context use rancher-desktop
docker compose -f deployment/compose.yaml up -d --build --wait
docker compose -f deployment/compose.yaml ps
python3 smoke_test.py
```

Book API docs: http://localhost:8001/docs

Order API docs: http://localhost:8002/docs

The Compose and Kubernetes files contain explicitly named local demo database passwords. Use these settings only for the local assignment demonstration; supply separate secrets for any real deployment.

## Tests

After installing both services' requirements in a virtual environment:

```bash
python3 -m unittest discover -s tests -v
```

The tests use temporary SQLite databases. The smoke test checks the running PostgreSQL-backed application and creates a demo book and order.

## Stop

```bash
docker compose -f deployment/compose.yaml stop
```

Named database volumes preserve the demo data. See `RUN_GUIDE.md` for API requests, Kubernetes commands and troubleshooting.
