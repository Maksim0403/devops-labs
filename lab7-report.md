# Лабораторна робота №7

## Observability: метрики, логи, дашборди й відкат за метриками

**Студент:** ____________________  
**Група:** ____________________  
**Дата:** ____________________

### Мета роботи

Зробити стан застосунку LogiFlow видимим за допомогою метрик і JSON-логів,
зібрати дані в Prometheus і Loki, показати їх на Grafana-дашборді та
перевірити автоматичне переривання невдалого canary-релізу за часткою
успішних HTTP-запитів.

### Середовище

- Kubernetes: Minikube, Docker driver.
- Доставка застосунку та observability-компонентів: Argo CD.
- Розгортання версій backend: Argo Rollouts, canary.
- Моніторинг: kube-prometheus-stack, Prometheus, Alertmanager, Grafana.
- Логи: Loki та Grafana Alloy.
- Namespace застосунку: `logiflow-argo`.
- Namespace моніторингу: `monitoring`.

> Перед здачею замінити блоки `Додати скриншот` на власні зображення з
> Grafana, Prometheus і Argo CD. Приклади команд нижче призначені для
> PowerShell.
>
> Ресурси дашборда, AnalysisTemplate і PrometheusRule додані до локальної
> версії GitOps-чарту. Щоб побачити їх у кластері, спочатку доставити зміни
> з GitOps-репозиторію; до цього часу наведені для них скриншоти залишаються
> незаповненими.

## 1. Стек моніторингу через Argo CD

Argo CD керує застосунками `kps`, `loki` та `alloy` з GitOps-репозиторію.
Kube-prometheus-stack надає Prometheus, Alertmanager і Grafana; Loki працює
в режимі SingleBinary; Alloy читає stdout контейнерів і надсилає записи в
Loki.

Перевірка стану:

```powershell
kubectl get applications -n argocd
kubectl get pods -n monitoring
kubectl port-forward -n monitoring svc/kps-grafana 3000:80
```

Відкрити `http://localhost:3000` і переконатися, що Grafana завантажується.

**Докази**

- Додати скриншот 1.1: Argo CD Applications зі станами `Synced` і `Healthy`.
- Додати скриншот 1.2: усі pod-и в `monitoring` у стані `Running`.
- Додати скриншот 1.3: відкрита Grafana.

## 2. Метрики застосунку

Backend надає `/metrics` з лічильником `http_requests_total` (мітки
`method`, `route`, `status`) і гістограмою
`http_request_duration_seconds` (мітка `route`). Метрики використовують
шаблони маршрутів FastAPI, а не повні URL, щоб не збільшувати кардинальність.
Helm-чарт створює ServiceMonitor для backend service.

Перевірка ServiceMonitor і scrape target:

```powershell
kubectl get servicemonitor -n logiflow-argo
kubectl port-forward -n monitoring svc/kps-prometheus 9090:9090
```

У Prometheus відкрити **Status → Targets**, знайти
`logiflow-logiflow-backend` і перевірити стан `UP`. У вкладці **Graph**
виконати:

```promql
sum(rate(http_requests_total{namespace="logiflow-argo"}[5m]))
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(http_request_duration_seconds_bucket{namespace="logiflow-argo"}[5m])
  )
)
```

**Докази**

- Додати скриншот 2.1: ServiceMonitor у namespace `logiflow-argo`.
- Додати скриншот 2.2: Prometheus target backend зі станом `UP`.
- Додати скриншот 2.3: результат запиту PromQL до `http_requests_total`.

## 3. Логи

Middleware backend виводить у stdout по одному JSON-об'єкту на HTTP-запит.
Запис містить час, рівень, повідомлення, метод, шаблон маршруту, HTTP-статус
і тривалість у мілісекундах. Alloy збирає логи pod-ів, Loki зберігає їх.

Щоб створити запити для перевірки, запустити з PowerShell:

```powershell
kubectl run curl-fail --rm -i --restart=Never --image=curlimages/curl -- sh -c 'for i in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null http://logiflow-logiflow-backend.logiflow-argo.svc:8000/fail; done'
```

У Grafana відкрити **Explore → Loki**, вибрати діапазон **Last 15 minutes**
і виконати запити окремо:

```logql
{namespace="logiflow-argo", pod=~"logiflow-logiflow-backend.*"}
```

```logql
{namespace="logiflow-argo", pod=~"logiflow-logiflow-backend.*"}
  | json
  | status_code >= 500
```

Для перегляду помилок лише від pod-ів версії `2.0.1`, після її випуску:

```logql
{namespace="logiflow-argo", pod=~"logiflow-logiflow-backend.*"}
  | json
  | status_code >= 500
  | version="2.0.1"
```

**Докази**

- Додати скриншот 3.1: Explore з першим запитом і JSON-рядками.
- Додати скриншот 3.2: Explore з другим запитом і записами зі статусом 500.

## 4. Дашборд

Helm-чарт містить Grafana dashboard JSON і створює ConfigMap з міткою
`grafana_dashboard: "1"`. Grafana sidecar, налаштований через kube-prometheus
stack, автоматично завантажує його. Дашборд `LogiFlow Observability` містить:

- кількість запитів за секунду;
- частку HTTP 5xx;
- p95 тривалості запитів;
- CPU і working-set пам'ять backend pod-ів;
- логи backend із фільтром 5xx у Loki.

Перевірка після синхронізації GitOps:

```powershell
kubectl get configmap -n logiflow-argo -l grafana_dashboard=1
argocd app get logiflow
```

У Grafana відкрити **Dashboards → LogiFlow Observability**.

**Докази**

- Додати скриншот 4.1: ConfigMap дашборда з міткою `grafana_dashboard`.
- Додати скриншот 4.2: Grafana dashboard з видимими панелями метрик і логів.

## 5. Навантаження

Запустити генератор запитів до `/slow` і `/version`. Команда працює до
натискання `Ctrl+C`; pod видалиться після завершення.

```powershell
kubectl run lab7-load --rm -it --restart=Never --image=curlimages/curl -- sh -c 'while true; do curl -s -o /dev/null http://logiflow-logiflow-backend.logiflow-argo.svc:8000/slow; curl -s -o /dev/null http://logiflow-logiflow-backend.logiflow-argo.svc:8000/version; done'
```

Залишити навантаження активним, відкрити дашборд і спостерігати за запитами
за секунду, затримкою та CPU. Для додаткової зміни викликати `/fail` або
тимчасово змінити `FAIL_RATE` через Git. Додатково PrometheusRule генерує
alert `LogiFlowHighHttp5xxRate`, якщо частка 5xx перевищує 5% протягом 1 хв.

**Докази**

- Додати скриншот 5.1: активне навантаження в терміналі.
- Додати скриншот 5.2: дашборд під навантаженням із помітною зміною RPS,
  p95 і CPU.
- Додати скриншот 5.3: інша зміна (наприклад, запити до `/fail`).

## 6. Автоматичний відкат за метриками

AnalysisTemplate `logiflow-success-rate` запитує Prometheus про частку
успішних запитів backend. Canary продовжується, якщо успішність не нижче
95%; інакше AnalysisRun завершується невдачею й Argo Rollouts перериває
canary. У `values-minikube.yaml` порогові налаштування задають інтервал
аналізу та canary steps.

Для демонстрації після коміту й доставки базової конфігурації:

1. Залишити генератор навантаження з пункту 5 активним.
2. У GitOps-репозиторії випустити нову версію backend (наприклад, образ
   `2.0.1`) і встановити `FAIL_RATE: "1"` у `charts/logiflow/values-minikube.yaml`.
3. Зробити commit і push. Дочекатися canary AnalysisRun і автоматичного
   abort; зафіксувати невдалий AnalysisRun та стабільні репліки.
4. Повернути `FAIL_RATE: "0"` і stable image tag у Git, зробити commit і
   push, дочекатися `Healthy`.
5. У Loki виконати запит із фільтром `version="2.0.1"` з пункту 3, щоб
   показати помилки pod-ів невдалої версії.

Корисні команди:

```powershell
kubectl get analysisruns -n logiflow-argo
kubectl get rollouts -n logiflow-argo
kubectl argo rollouts get rollout logiflow-logiflow-backend -n logiflow-argo
argocd app get logiflow
```

Якщо команда `kubectl argo rollouts` недоступна, встановити Argo Rollouts
kubectl plugin або переглянути об'єкти через `kubectl get rollouts` та
`kubectl describe analysisrun -n logiflow-argo <ім'я>`.

**Докази**

- Додати скриншот 6.1: новий GitOps commit зі зміненими образом і
  `FAIL_RATE`.
- Додати скриншот 6.2: AnalysisRun у стані `Failed` і Rollout після abort.
- Додати скриншот 6.3: дашборд зі сплеском 5xx під час canary.
- Додати скриншот 6.4: логи 5xx із `version` невдалого релізу.
- Додати скриншот 6.5: Prometheus alert у стані `Firing`.
- Додати скриншот 6.6: Git-коміт відновлення stable tag і `FAIL_RATE: "0"`.
- Додати скриншот 6.7: Rollout і Argo CD після відновлення у стані `Healthy`.

## 7. Захист: лайв-демонстрація

Показати Prometheus target `UP`, виконати довільний PromQL, відкрити
дашборд під навантаженням, відфільтрувати 5xx у Loki та продемонструвати
невдалий реліз із автоматичним abort і поверненням на stable.

**Докази**

- Додати скриншот 7.1: фінальний огляд (Prometheus, dashboard, Loki або
  Argo Rollouts) для захисту.

## Внесені зміни

- Backend: метрики запитів і затримки, JSON access logs у stdout,
  `/metrics`, `/fail`, `/slow`, кероване середовищем `FAIL_RATE`.
- GitOps Helm chart: ServiceMonitor, dashboard ConfigMap і AnalysisTemplate
  для перевірки success rate перед наступним canary-кроком.
- Monitoring Argo CD applications: kube-prometheus-stack, Loki та Alloy.

## Результати перевірок

| Перевірка | Результат |
|---|---|
| `uv run ruff check .` | Успішно |
| `uv run pytest` | 22 passed, 3 skipped |
| `helm lint charts/logiflow` | Успішно, 1 необов'язкове попередження про icon |
| Prometheus backend target | 5 targets зі станом `UP` |
| Loki LogQL для 5xx | Повертає записи зі статусом 500 |
| GitOps applications | `Synced` і `Healthy` |
| AnalysisRun невдалого релізу | Потрібно виконати після доставки локальних GitOps-змін |
| Автоматичний abort і stable після відкату | Потрібно продемонструвати під час пункту 6 |
