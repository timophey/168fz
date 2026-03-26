# Docker Развертывание 168-ФЗ Text Checker

Микросервис для проверки текстов на соответствие закону № 168-ФЗ с веб-интерфейсом и REST API.

## 🚀 Быстрый старт

### Использование Make (рекомендуется)

```bash
# Сборка и запуск
make up

# Откроется в браузере: http://localhost:8000

# Просмотр логов
make logs

# Остановка
make down
```

### Или через Docker Compose

```bash
# Сборка и запуск
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f checker

# Остановка
docker-compose down
```

## 🌐 Доступные адреса

- **Веб-интерфейс**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/api/v1/health

## 📋 Makefile команды

| Команда | Описание |
|---------|----------|
| `make build` | Сборка Docker образа |
| `make up` | Запуск контейнера (detached) |
| `make down` | Остановка контейнера |
| `make logs` | Просмотр логов в реальном времени |
| `make test` | Тест API (требует curl и jq) |
| `make sync` | Синхронизация всех словарей |
| `make shell` | Открыть bash в контейнере |
| `make clean` | Остановка и удаление образа |
| `make help` | Показать эту справку |

## 🔧 REST API

### Основные endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/` | Веб-интерфейс |
| `GET` | `/api/v1/health` | Проверка здоровья |
| `POST` | `/api/v1/check` | Проверка текста (JSON: {"text": "..."} или {"url": "..."}) |
| `POST` | `/api/v1/check/file` | Проверка загруженного файла (multipart/form-data) |
| `GET` | `/api/v1/dictionaries` | Список словарей |
| `GET` | `/api/v1/dictionaries/{name}` | Информация о словаре |
| `POST` | `/api/v1/dictionaries/load` | Загрузка словаря |
| `GET` | `/api/v1/sync/status` | Статус синхронизации |
| `POST` | `/api/v1/sync/{dict_name}` | Синхронизация словаря |
| `POST` | `/api/v1/sync/all` | Синхронизация всех |
| `GET` | `/api/v1/sources` | Список источников |

### Примеры запросов

#### Проверка текста
```bash
curl -X POST "http://localhost:8000/api/v1/check" \
  -H "Content-Type: application/json" \
  -d '{"text": "Наш developer провел meeting"}'
```

#### Проверка URL
```bash
curl -X POST "http://localhost:8000/api/v1/check" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

#### Проверка файла
```bash
curl -X POST "http://localhost:8000/api/v1/check/file" \
  -F "file=@document.txt"
```

#### Синхронизация всех словарей
```bash
curl -X POST "http://localhost:8000/api/v1/sync/all"
```

#### Список словарей
```bash
curl "http://localhost:8000/api/v1/dictionaries"
```

## 📁 Структура volumes

Для сохранения данных между перезапусками используются volumes:

- `./dictionaries/data` - загруженные словари
- `./sync/cache` - кэш и метаданные синхронизации
- `./config` - конфигурационные файлы

Эти папки создаются автоматически при первом запуске.

## ⚙️ Конфигурация

### Переменные окружения

Переменные можно задать в `docker-compose.yml` или через командную строку:

```bash
# Кастомный порт
PORT=8080 docker-compose up -d

# Или в docker-compose.yml:
# environment:
#   - PORT=8080
```

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `PORT` | 8000 | Порт сервера |
| `HOST` | 0.0.0.0 | Хост для привязки |
| `DICTIONARIES_DIR` | /app/dictionaries/data | Путь к словарям |
| `DEBUG` | false | Режим отладки |

### Изменение порта

В `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # хост:контейнер
```

Или через командную строку:
```bash
docker-compose up -d -p 8080:8000
```

## 🔄 Синхронизация словарей

При первом запуске словари могут быть не синхронизированы.

### Автоматическая синхронизация

Через веб-интерфейс:
1. Откройте http://localhost:8000
2. В боковой панели нажмите "Синхронизировать все словари"

Через API:
```bash
curl -X POST "http://localhost:8000/api/v1/sync/all"
```

Через Make:
```bash
make sync
```

Через docker-compose exec:
```bash
docker-compose exec checker python sync_cli.py --sync all
```

### Доступные источники

**Автоматические:**
- ru_words_github (200K+ слов)
- hunspell_ru (LibreOffice словарь)
- opencorpora (500K+ словоформ)
- foreign_words_github
- obscene_github
- thesaurus_github

**Legacy (требуют ручной настройки):**
- gramota_ru
- opencorpora_official

## 🧪 Тестирование

### Быстрая проверка

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Ожидаемый ответ:
# {"status":"healthy","service":"168-ФЗ Text Checker","version":"1.0.0"}
```

### Тестовая проверка текста

```bash
curl -X POST "http://localhost:8000/api/v1/check" \
  -H "Content-Type: application/json" \
  -d '{"text": "Это тестовый текст для проверки"}'
```

### Использование make test

```bash
make test
```

Требует установленного `curl` и `jq` (опционально для красивого вывода).

## 🐛 Устранение неполадок

### Контейнер не запускается

```bash
# Проверить логи
docker-compose logs checker

# Проверить, что порт свободен
netstat -tulpn | grep :8000
```

### Ошибка при синхронизации

```bash
# Проверить сетевой доступ
docker-compose exec checker ping -c 3 github.com

# Запустить синхронизацию вручную
docker-compose exec checker python sync_cli.py --sync all --force
```

### Словари не загружены

```bash
# Проверить, что volume смонтирован
docker-compose exec checker ls -la /app/dictionaries/data/

# Запустить синхронизацию
make sync
```

### Очистка и пересборка

```bash
# Полная очистка
make clean

# Удалить volumes (ВНИМАНИЕ: удалятся словари!)
docker-compose down -v

# Пересборка
make build
make up
```

## 📊 Мониторинг

### Просмотр статуса

```bash
# Статус контейнера
docker-compose ps

# Использование ресурсов
docker stats fz168-checker

# Логи
docker-compose logs --tail=100 checker
```

### API статус

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Статус словарей
curl http://localhost:8000/api/v1/sync/status
```

## 🔒 Безопасность

### Настройка CORS

По умолчанию CORS разрешен для всех источников (`*`). Для production настройте в `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ваш-сайт.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Запуск без привилегий

Контейнер запускается от root по умолчанию. Для повышения безопасности:

```dockerfile
# В Dockerfile добавить перед CMD:
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

## 📈 Производительность

### Оптимизация для production

1. **Отключить reload** в uvicorn:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. **Использовать gunicorn**:
```dockerfile
RUN pip install gunicorn
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app"]
```

3. **Кэширование словарей**:
- Словари кэшируются в volume `./dictionaries/data`
- Не пересобирайте образ при обновлении словарей

## 🚀 Production развертывание

### Docker Swarm / Kubernetes

Для оркестрации используйте стандартные Docker образы. Пример docker-compose для production:

```yaml
version: '3.8'
services:
  checker:
    image: fz168-checker:latest
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
    ports:
      - "8000:8000"
    volumes:
      - dictionaries_data:/app/dictionaries/data
      - sync_cache:/app/sync/cache
    environment:
      - DICTIONARIES_DIR=/app/dictionaries/data
      - DEBUG=false
    restart: always

volumes:
  dictionaries_data:
  sync_cache:
```

### HTTPS

Используйте reverse proxy (nginx, Traefik) для HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name checker.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📝 Лицензия

Проект создан в образовательных целях. Используйте на свой страх и риск.

## 🔗 Ссылки

- [Основной README](../README.md)
- [Закон № 168-ФЗ](http://publication.pravo.gov.ru/Document/View/0001202407200010)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

## 📈 Возможности веб-интерфейса

### Проверка текста

Веб-интерфейс поддерживает три способа ввода:

1. **Прямой текст** - введите текст в текстовое поле
2. **URL** - введите адрес веб-страницы, текст будет извлечен автоматически
3. **Файл** - загрузите файл (TXT, MD, HTML, JSON, CSV)

### Результаты проверки

- Статистика: количество слов, уникальных слов
- Запрещенные слова (выделены красным)
- Иностранные слова (выделены желтым) с рекомендациями
- Нарушения норм русского языка (выделены синим)
- Уровень риска (низкий/средний/высокий)
- Скачивание отчета в формате JSON или TXT

### Мониторинг

- Просмотр загруженных словарей
- Статус синхронизации каждого словаря
- Количество слов в каждом словаре
- Список доступных источников

### Управление

- Синхронизация всех словарей одной кнопкой
- Загрузка пользовательских словарей
- Просмотр информации об источниках
