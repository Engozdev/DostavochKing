# Автотесты

Тесты находятся только в `tests/` и разделены по назначению:

| Папка | Что проверяет |
| --- | --- |
| `unit/` | Правила корзины, заказа и платежей без базы данных |
| `integration/` | Работу сервисов с PostgreSQL: корзина, оформление, оплата, доставка |
| `e2e/` | Пользовательский путь через HTTP-интерфейс Django |

Каждый сценарий помечен `@step` с понятным названием. Сквозные тесты используют HTTP-клиент Django; браузер и внешняя платёжная система в них не участвуют.

## Запуск

Нужны Python 3.12, зависимости из `requirements.txt` и PostgreSQL с правом создания тестовой базы. В корне проекта:

```powershell
python -m pip install -r requirements.txt
$env:DJANGO_SECRET_KEY = 'local-test-key-only'
$env:POSTGRES_DB = 'dostavochking'
$env:POSTGRES_USER = 'dostavochking'
$env:POSTGRES_PASSWORD = '<пароль тестовой БД>'
$env:POSTGRES_HOST = '127.0.0.1'
$env:POSTGRES_PORT = '5433'
python -m tests.run
```

Если используется Docker Compose, после настройки `.env` достаточно:

```powershell
docker compose up -d db
New-Item -ItemType Directory -Force .\test-results | Out-Null
docker compose run --rm --volume "${PWD}/tests:/app/tests" --volume "${PWD}/test-results:/app/test-results" web python -m tests.run
```

Тома передают контейнеру актуальную папку `tests` и сохраняют HTML/JSON-отчёты на компьютере. Без них `docker compose run` использует файлы из ранее собранного образа, а отчёты исчезают после удаления временного контейнера.

Скрипт обновляет `test-results/results.json`, `test-results/report.html` и `test-results/presentation.html`. `presentation.html` для показа коллегам; подробности каждого теста в `report.html`. Диаграммы строятся из результатов запуска, поэтому отдельные скриншоты предоставлять не нужно. Если тесты не стартовали, отчёт показывает причину и не выдаёт сценарии за пройденные.
