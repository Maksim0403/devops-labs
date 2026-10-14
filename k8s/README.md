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

З кореня репозиторію:

```
minikube start --driver=docker
minikube addons enable metrics-server
minikube addons enable ingress
minikube image load ghcr.io/maksim0403/devops-labs-backend:1.0.0
minikube image load ghcr.io/maksim0403/devops-labs-frontend:1.0.0
kubectl apply -f k8s/
kubectl get all,pvc,ingress -n logiflow
```

PostgreSQL використовує образ `postgres:17-alpine`. Backend має TCP liveness- і readiness-проби на порт `8000`; frontend має HTTP liveness- і readiness-проби для шляху `/` на порт `80`; PostgreSQL перевіряється командою `pg_isready`.

Для доступу через Ingress запустіть port-forward в окремому терміналі:

```
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
```

Відкрийте `http://localhost:8080`. Альтернативно, frontend доступний через NodePort: `minikube service frontend -n logiflow --url`.

## ConfigMap `logiflow-config`

| Параметр | Значення | Призначення |
|---|---|---|
| `DEBUG` | `false` | Режим налагодження |
| `DB_HOST` | `postgres` | Ім'я Service PostgreSQL |
| `DB_PORT` | `5432` | Порт PostgreSQL |
| `DB_NAME` | `logiflow` | Назва бази даних |
| `DB_USER` | `logiflow` | Користувач бази даних |
| `ALGORITHM` | `HS256` | Алгоритм підпису токенів |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Час життя access-токена у хвилинах |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Час життя refresh-токена у днях |
| `COOKIE_SECURE` | `false` | Дозволяє cookie без Secure для HTTP |
| `CORS_ORIGINS` | `http://localhost,http://127.0.0.1` | Дозволені джерела CORS |
| `AVERAGE_SPEED_KMH` | `60.0` | Середня швидкість для розрахунків |
| `S3_ENDPOINT_URL` | `http://seaweedfs:8333` | Адреса S3-сумісного сховища |
| `S3_BUCKET_NAME` | `logiflow-storage` | Назва S3 bucket |
| `S3_REGION` | `us-east-1` | Регіон S3 |

## Secret `logiflow-secret`

| Параметр | Призначення |
|---|---|
| `DB_PASSWORD` | Навчальний пароль PostgreSQL |
| `SECRET_KEY` | Навчальний ключ підпису токенів |
| `S3_ACCESS_KEY` | Навчальний ключ доступу до S3 |
| `S3_SECRET_KEY` | Навчальний секретний ключ S3 |

Усі значення Secret — навчальні й не повинні використовуватися для робочих систем.
