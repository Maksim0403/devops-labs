# LogiFlow — лабораторна робота №4

## Helm-чарт

Чарт застосунку розташований у `helm/logiflow`. Він створює ConfigMap, Secret, PVC PostgreSQL (опційно), Deployment і Service PostgreSQL, Job міграцій Alembic, Deployment і Service backend та frontend, а також Ingress (опційно). Усі імена прив'язані до Helm-релізу, тому чарт можна встановити кілька разів в одному кластері й namespace.

`version` у `Chart.yaml` — версія пакунка Helm-чарта (змінюється при зміні шаблонів або значень чарта); `appVersion` — версія застосунку LogiFlow, який пакується чартом. Це незалежні версії: новий чарт не обов'язково означає новий образ застосунку.

Namespace чарт не створює: його створює Helm опцією `--create-namespace`.

## Параметри values

| Параметр | Тип / приклад | Значення за замовчуванням | Призначення |
|---|---|---|---|
| `images.backend.repository` / `images.backend.tag` | рядки | `ghcr.io/maksim0403/devops-labs-backend:1.0.0` | Репозиторій і тег backend |
| `images.frontend.repository` / `images.frontend.tag` | рядки | `ghcr.io/maksim0403/devops-labs-frontend:1.0.0` | Репозиторій і тег frontend |
| `images.postgres.repository` / `images.postgres.tag` | рядки | `postgres:17-alpine` | Образ PostgreSQL |
| `backend.replicas`, `frontend.replicas`, `postgres.replicas` | цілі числа | `2`, `2`, `1` | Кількість реплік відповідних Deployment |
| `backend.service.type`, `backend.service.port` | рядок, число | `ClusterIP`, `8000` | Тип та порт Service backend |
| `frontend.service.type`, `frontend.service.port`, `frontend.service.nodePort` | рядок, числа | `NodePort`, `80`, `30080` | Тип та порти Service frontend |
| `backend.resources`, `frontend.resources`, `postgres.resources` | Kubernetes resources | development profile | CPU та пам'ять (requests/limits) |
| `config.*` | рядки | значення з `values.yaml` | Нечутлива конфігурація програми; `DB_HOST` і `DB_PORT` виводяться з налаштувань PostgreSQL |
| `secret.*` | рядки | лише навчальні заглушки | Значення Kubernetes Secret; замініть перед використанням поза локальною лабораторною |
| `postgres.persistence.enabled` | boolean | `true` | Створювати PVC; при `false` дані PostgreSQL зберігаються в тимчасовому `emptyDir` |
| `postgres.persistence.size`, `postgres.persistence.accessModes` | рядок, список | `1Gi`, `ReadWriteOnce` | Розмір і режим доступу PVC |
| `ingress.enabled` | boolean | `false` | Створювати Ingress |
| `ingress.className`, `ingress.host`, `ingress.annotations`, `ingress.tls` | рядок/мапи/списки | `nginx`, порожньо | Налаштування Ingress |
| `helmTest.enabled` | boolean | `true` | Вмикати тест доступності backend для `helm test` |

Реальні паролі та ключі не зберігайте у файлах значень або в репозиторії. Значення `secret.*` у чарта — тільки демонстраційні заглушки. Для реального розгортання під'єднайте окремий Secret, створений системою керування секретами, та розширте чарт підтримкою наявного Secret.

## Профілі середовищ

Порівняти значення без встановлення релізу:

```powershell
helm template logiflow .\helm\logiflow -f .\helm\logiflow\values-dev.yaml > "$env:TEMP\logiflow-dev.yaml"
helm template logiflow .\helm\logiflow -f .\helm\logiflow\values-prod.yaml > "$env:TEMP\logiflow-prod.yaml"
Compare-Object (Get-Content "$env:TEMP\logiflow-dev.yaml") (Get-Content "$env:TEMP\logiflow-prod.yaml")
```

Профілі різняться репліками, ресурсами, тегами образів і Ingress. `latest` для prod є прикладом: у реальному середовищі задавайте незмінний тег образу.

Для одного параметра пріоритет такий: значення `values.yaml` чарта < значення файлів `-f` (пізніший файл перекриває попередній) < прапорці `--set` / `--set-string`. Щоб порівняти середовища, не встановлюючи їх у кластер, застосуйте `helm template` окремо до кожного профілю.

## Встановлення

Потрібні Helm 3, запущений minikube з Ingress addon для профілю prod та опубліковані образи застосунку. Для локальних непублікованих образів зберіть і завантажте їх у minikube; за замовчуванням використовується `IfNotPresent`.

```powershell
minikube start --driver=docker
minikube addons enable ingress
helm lint .\helm\logiflow
helm template logiflow .\helm\logiflow -n logiflow-helm -f .\helm\logiflow\values-dev.yaml
helm install logiflow .\helm\logiflow -n logiflow-helm --create-namespace -f .\helm\logiflow\values-dev.yaml --set frontend.service.type=ClusterIP --wait
```

Development-команда вище встановлює реліз в окремий namespace і використовує `ClusterIP`, щоб не конфліктувати з NodePort сервісом лабораторної №3. У чистому кластері прапорець `--set frontend.service.type=ClusterIP` можна прибрати, щоб використати NodePort з dev-профілю. Встановити production-профіль можна в іншому namespace:

```powershell
helm install logiflow-prod .\helm\logiflow -n logiflow-prod --create-namespace -f .\helm\logiflow\values-prod.yaml --wait
```

## Оновлення, історія та відкат

Наступні команди демонструють зміну тегу через `--set`, оновлення з іншим профілем, перегляд стану та відкат. Перша команда створює ревізію з новим frontend-тегом, друга — наступну ревізію зі значеннями prod, а відкат до ревізії 2 повертає dev-профіль із тегом `1.1.0`. Helm створить для відкату нову ревізію історії.

```powershell
helm upgrade logiflow .\helm\logiflow -n logiflow-helm --reuse-values --set images.frontend.tag=1.1.0 --wait
helm upgrade logiflow .\helm\logiflow -n logiflow-helm -f .\helm\logiflow\values-prod.yaml --wait
helm list -n logiflow-helm
helm status logiflow -n logiflow-helm
helm get values logiflow -n logiflow-helm --all
helm history logiflow -n logiflow-helm
helm rollback logiflow 2 -n logiflow-helm --wait
helm history logiflow -n logiflow-helm
helm test logiflow -n logiflow-helm
```

`helm list` показує стан релізу; `helm get values --all` — об'єднані значення. Helm за замовчуванням зберігає стан у Kubernetes Secret у namespace релізу (секрети мають імена на кшталт `sh.helm.release.v1.logiflow.v1`): переглянути їх можна командою `kubectl get secrets -n logiflow-helm -l owner=helm`.

Видалення релізу та перевірка namespace:

```powershell
helm uninstall logiflow -n logiflow-helm
kubectl get all,pvc,ingress,secret -n logiflow-helm
```

Після видалення Helm-релізу перелічені chart-ресурси мають бути відсутні. Helm не видаляє namespace, створений через `--create-namespace`; у ньому залишається системний ConfigMap `kube-root-ca.crt`. Для повного видалення namespace окремо виконайте `kubectl delete namespace logiflow-helm`, якщо він більше не потрібен.

## Вибране завдання: тест релізу

`templates/tests/test-backend.yaml` визначає Helm test hook: Pod із backend-образом запитує `/api/v1/health` у Service backend і завершується помилкою, якщо HTTP-відповідь неуспішна. Swagger/OpenAPI у production-встановленні вимкнені, тому для тесту використовується health endpoint. Виконання: `helm test logiflow -n logiflow-helm`.

## Звіт і демонстрація

Фактичні результати перевірки пунктів 6–9, стан release history та підсумок очищення середовища наведено у [`lab4-report.md`](lab4-report.md):

Звітні докази для здачі: `helm lint`, два рендеринги `helm template`, `helm list/status/get values`, список Helm Secrets, історія чотирьох ревізій, успішний `helm test` і відсутність ресурсів релізу після `helm uninstall`.

`k8s/README.md` описує підготовку й запуск застосунку з маніфестів лабораторної №3. Поточний кластер вже містить ресурси лабораторної №3 у namespace `logiflow`, зокрема PVC з даними PostgreSQL. Щоб не конфліктувати й не видалити ці дані під час демонстрації, використовуйте для чарта окремий namespace, наприклад `logiflow-helm`, та змініть у командах вище імена релізу/namespace на `logiflow-helm`. Видаляйте ресурси старої лабораторної лише після окремого збереження даних і якщо це потрібно для здачі.
