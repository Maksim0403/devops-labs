# Розгортання LogiFlow у Kubernetes (minikube)

Namespace: `logiflow`. Усі маніфести в цьому каталозі, по одному файлу на об'єкт.

## Склад

| Файл | Об'єкт |
|---|---|
| 00-namespace.yaml | Namespace |
| 01-configmap.yaml | ConfigMap з параметрами застосунку |
| 02-secret.yaml | Secret із чутливими параметрами |
| 03-postgres-pvc.yaml | PersistentVolumeClaim для БД |
| 04, 05 | Deployment і Service PostgreSQL |
| 06-migrate-job.yaml | Job з міграціями Alembic |
| 07, 08 | Deployment (2 репліки) і Service backend |
| 09, 10 | Deployment (2 репліки) і Service (NodePort) frontend |
| 11-ingress.yaml | Ingress: `/` до frontend, `/api` до backend |

## Порядок розгортання

```
minikube start --driver=docker
minikube addons enable metrics-server
minikube addons enable ingress
minikube image load ghcr.io/maksim0403/devops-labs-backend:1.0.0
minikube image load ghcr.io/maksim0403/devops-labs-frontend:1.0.0
kubectl apply -f k8s/
kubectl get all -n logiflow
```

Доступ: `minikube service frontend -n logiflow --url` або `minikube tunnel` і адреса `http://127.0.0.1`.

## ConfigMap `logiflow-config`

| Параметр | Значення | Призначення |
|---|---|---|
| DEBUG | false | режим налагодження |
| LOG_LEVEL | INFO | рівень логування |
| DB_HOST, DB_PORT | postgres, 5432 | адреса БД (Service) |
| DB_NAME, DB_USER | logiflow | база та користувач |
| COOKIE_SECURE | false | cookie без Secure для HTTP |
| CORS_ORIGINS | localhost | дозволені джерела |
| S3_ENDPOINT_URL, S3_BUCKET_NAME, S3_REGION | | параметри S3-сховища |

## Secret `logiflow-secret`

DB_PASSWORD, SECRET_KEY, S3_ACCESS_KEY, S3_SECRET_KEY. Значення навчальні, не від робочих систем.
