# Run the Online Bookstore on Rancher Desktop for macOS

This repository contains the runnable application. The assignment report is submitted separately.

## 1 Start Rancher Desktop

Open Rancher Desktop from Applications. In Preferences → Container Engine,
select **dockerd (Moby)**, apply and wait for the engine to finish starting.
The built-in Kubernetes cluster is optional for the Compose phase. The
assignment's Minikube deployment is a separate phase below.

In Terminal:

```bash
cd online-bookstore
docker context use rancher-desktop
docker version
```

`docker version` must show both Client and Server. A missing `.rd/docker.sock`
means the Docker engine is not available yet; check Rancher Desktop startup
and that Moby is selected. Do not proceed until Server information appears.

## 2 Build and start four containers

```bash
docker compose -f deployment/compose.yaml up -d --build --wait
docker compose -f deployment/compose.yaml ps
```

The first build downloads Python, PostgreSQL and Python dependencies and can
take several minutes. The database containers initialize their schemas only
when their persistent data directories are empty. The application starts after
database readiness checks. This project uses local demonstration passwords.

You should see book-db, order-db, book-service and order-service healthy.

Open these addresses in your browser:

- Book API documentation: http://localhost:8001/docs
- Order API documentation: http://localhost:8002/docs

Each API documentation page has **Try it out** buttons.

## 3 Check the full flow automatically

With Python 3 available:

```bash
python3 smoke_test.py
```

The script creates a book, retrieves it, creates an order, verifies a total
of 900.00 and checks quantity validation. It adds one book and one order on
each run. It uses only Python's standard library on the host.

For isolated service tests without installing packages on the host:

```bash
docker compose -f deployment/compose.yaml run --rm --no-deps -v "$PWD/tests:/tests:ro" -v "$PWD/book-service:/book-service:ro" -v "$PWD/order-service:/order-service:ro" book-service python -m unittest discover -s /tests -v
```

These behaviour tests use temporary SQLite databases. The smoke test checks
the actual PostgreSQL container integration.

## 4 Verify in Postman and capture screenshots

Import `Bookstore.postman_collection.json` using File → Import. Run **Create
book** first; its response script stores `book_id`. Run **Get book**, then
**Create order**, then **Get order**. The order response script stores
`order_id`. Finally run **Invalid quantity** and **Unknown book**.

Alternatively use these requests manually:

1. POST http://localhost:8001/books, Body → raw → JSON:

```json
{"title":"Distributed Systems Basics","author":"Sample Author","price":"450.00"}
```

2. Copy the returned ID. POST http://localhost:8002/orders:

```json
{"book_id":1,"quantity":2}
```

Replace 1 with the actual book ID. Expect HTTP 201 and total_price 900.00.
Retrieve using GET http://localhost:8002/orders/RETURNED_ORDER_ID.

## 5 View logs and stop the application

```bash
docker compose -f deployment/compose.yaml logs --tail=100 book-service order-service
docker compose -f deployment/compose.yaml stop
```

Use `docker compose -f deployment/compose.yaml start` to resume the stopped
stack. Named database volumes preserve records. Compose data and Kubernetes
data are separate: create a new book when moving to Kubernetes.

## 6 Install and start Minikube for the assignment

Keep Rancher Desktop running with Moby selected. If using Homebrew, install
Minikube (and kubectl only if it is missing):

```bash
brew install minikube
```

```bash
brew install kubectl
```

Stop the Compose stack before starting Minikube to free host ports and memory.
If the Rancher Desktop built-in cluster is unused, disable it in Preferences
→ Kubernetes. Ensure the Rancher VM has enough resources for the requested
4 GiB Minikube allocation plus the engine; 6 GiB or more is a useful starting
allocation if your Mac has capacity.

```bash
docker compose -f deployment/compose.yaml stop
minikube start --driver=docker --cpus=2 --memory=4096
kubectl config use-context minikube
kubectl get nodes
minikube image load book-service:1.0
minikube image load order-service:1.0
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/resources.yaml
kubectl rollout status deployment/book-db -n bookstore --timeout=180s
kubectl rollout status deployment/order-db -n bookstore --timeout=180s
kubectl rollout status deployment/book-service -n bookstore --timeout=180s
kubectl rollout status deployment/order-service -n bookstore --timeout=180s
kubectl get pods,services,pvc -n bookstore
```

The manifests are written in JSON syntax, which kubectl accepts as YAML.
They create four Deployments, four Services, two PVCs, two schema ConfigMaps
and a Secret containing local demonstration database configuration. Real
production secrets should be supplied separately.

In **Terminal 1**:

```bash
kubectl port-forward -n bookstore service/book-service 8001:8000
```

In **Terminal 2**:

```bash
kubectl port-forward -n bookstore service/order-service 8002:8000
```

Leave both terminals running. In **Terminal 3**, return to this folder and run
`python3 smoke_test.py`, or run the Postman collection again to create fresh
Kubernetes records and capture the API evidence.

## 7 Dashboard and scaling evidence

```bash
kubectl scale deployment/book-service --replicas=2 -n bookstore
kubectl rollout status deployment/book-service -n bookstore
kubectl get pods -n bookstore
minikube dashboard
```

Select the bookstore namespace. Capture Deployments, Pods, Services and PVCs.
For restart persistence, note an order ID, restart the Order service, wait for
rollout and retrieve that order again:

```bash
kubectl rollout restart deployment/order-service -n bookstore
kubectl rollout status deployment/order-service -n bookstore
```

Restart its port-forward command if the forwarding session disconnects.
Port forwarding can disconnect when its selected pod is replaced.

For the dependency failure check, scale Book service to zero, send POST
/orders and expect 503, then restore its replicas to two. Reestablish Book
port forwarding after pods are ready.

## 8 Final submission

The implementation keeps the models, validation and routes in each service's
`app/main.py` for a small demonstration. Update the report's proposed module
tree to this actual layout, and mention the quantity upper bound of 100.
Create a separate GitHub repository from each service directory and add the
URLs to the report. Include the SQL schema and service README in each repo.
Save deployment files in one clearly linked repository or a third deployment
repository. Replace test and screenshot placeholders with actual evidence.

## Troubleshooting

| Symptom | Check |
|---|---|
| Docker socket missing | Rancher Desktop started, Moby selected, engine ready |
| Port 8001 or 8002 in use | Stop previous Compose services or port forwards |
| Container unhealthy | `docker compose -f deployment/compose.yaml logs --tail=100` |
| ImagePullBackOff | Load both images into Minikube and confirm exact 1.0 tags |
| API readiness fails | Database initialization, credentials and logs |
| PVC Pending | `kubectl describe pvc -n bookstore`; verify storage provisioner |
| Request fails after pod restart | Restart the affected port-forward command |
| Minikube memory error | Increase the Rancher VM allocation or stop other workloads |

At the time these files were prepared, the Docker engine was unavailable.
Do not treat expected output in this guide as a recorded deployment result.
