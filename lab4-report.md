# Звіт: лабораторна робота №4 — пакування LogiFlow у Helm-чарт

Дата виконання: 14.10.2026  
Чарт: `helm/logiflow`, `version: 0.1.0`, `appVersion: 1.0.0`  
Інструменти: Helm `v3.17.3`, minikube `v1.39.0`.

## 6. Профілі середовищ

`helm template` успішно зрендерив окремо dev і prod без створення релізів. У dev задано по одній репліці backend/frontend, образи з тегом `1.0.0`, Ingress вимкнено; у prod — по три репліки, образи `latest`, більші requests/limits і Ingress увімкнено. PVC PostgreSQL у обох профілях увімкнений. У фактичному dev-релізі тип frontend Service було перевизначено на `ClusterIP`, аби уникнути конфлікту NodePort `30080` з лабораторною №3.

Пріоритет значень: `values.yaml` < файли `-f` у порядку передавання (пізніший файл має пріоритет) < `--set`/`--set-string`. Це показано на зміні `images.frontend.tag` у ревізії 2.

## 7. Перевірка та встановлення

`helm lint` завершився успішно: `1 chart(s) linted, 0 chart(s) failed`. Dev- і prod-маніфести рендеряться. Порівняння з `k8s/` підтверджує ті самі основні ресурси застосунку: ConfigMap, Secret, PVC, PostgreSQL Deployment/Service, міграцію Alembic, backend Deployment/Service, frontend Deployment/Service та умовний Ingress. Імена мають префікс релізу; namespace створюється опцією Helm, а не шаблоном чарта.

Реліз встановлено командою:

```powershell
helm install logiflow .\helm\logiflow -n logiflow-helm --create-namespace -f .\helm\logiflow\values-dev.yaml --set frontend.service.type=ClusterIP --wait
```

Початковий статус — `deployed`, ревізія 1. Під час перевірки `helm list`, `helm status` та `helm get values --all` показували реліз і значення dev-профілю з перевизначеним frontend Service. Стан Helm зберігався в Secrets namespace релізу: `sh.helm.release.v1.logiflow.v1` і наступних ревізійних Secrets.

## 8. Життєвий цикл релізу

| Ревізія | Операція | Зміна | Статус перед наступною операцією |
|---:|---|---|---|
| 1 | `helm install` з dev-файлом | Backend/frontend `1.0.0`, одна репліка | `superseded` |
| 2 | `helm upgrade --reuse-values --set images.frontend.tag=1.1.0` | Змінено тег frontend на `1.1.0` | `superseded` |
| 3 | `helm upgrade -f values-prod.yaml` | Образи `latest`, три репліки backend/frontend, увімкнено Ingress | `superseded` |
| 4 | `helm rollback logiflow 2` | Відновлено dev-конфігурацію ревізії 2; rollback записаний як нова ревізія | `deployed` |

У prod frontend/backend були готові по 3/3 репліки; Ingress використовував клас `nginx`. `helm test logiflow -n logiflow-helm` успішно завершився в dev, prod і після rollback. Тест перевіряє `GET /api/v1/health` Service backend.

Після перевірки виконано `helm uninstall logiflow -n logiflow-helm`. `kubectl get all,pvc,ingress,secret -n logiflow-helm` підтвердив відсутність ресурсів релізу. Namespace лишився з системним ConfigMap `kube-root-ca.crt`.

## 9. Додаткове завдання

Реалізовано Helm test hook у `templates/tests/test-backend.yaml`; він запускає запит health endpoint з backend-образу. `helm test` завершився зі статусом `Succeeded`.

## Зауваження до середовища

У кластері до роботи вже працював застосунок лабораторної №3 у namespace `logiflow`, разом із PVC PostgreSQL `postgres-data`. Щоб не видаляти наявні дані, Helm-реліз лабораторної №4 перевірявся в окремому namespace `logiflow-helm`; після перевірки видалено лише цей Helm-реліз. Попередній workload і PVC лабораторної №3 залишилися незмінними.
