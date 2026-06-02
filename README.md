# personal_notify

Персональный Telegram-бот: оповещения по расписанию и по событиям, ответы на команды.
Для обработки текста оповещений используется локальная LLM (Ollama).

## Возможности

- Оповещения по расписанию через системный cron (пример: погода по Москве в 08:00 МСК).
- Прогноз погоды через провайдер Gismeteo (общий интерфейс — провайдер легко заменить).
- Обвязка вокруг локальной Ollama: обработка текста оповещений, выбор модели и опции.
- Команды `/start`, `/help`, `/status`; доступ только для владельца (whitelist по user_id).

## Установка

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .          # для разработки: -e ".[dev]"
cp .env.example .env                # заполнить BOT_TOKEN, ALLOWED_USER_ID, GISMETEO_TOKEN
cp config.example.yaml config.yaml  # модель Ollama, локация, хранилище
```

## Запуск

Демон бота (команды):

```bash
.venv/bin/python -m bot.main
```

Оповещение по расписанию — через cron (строка crontab):

```
CRON_TZ=Europe/Moscow
0 8 * * * cd /path/to/personal_notify && .venv/bin/python -m bot.tasks weather
```

## Деплой

Демон бота как systemd-сервис:

```bash
sudo cp deploy/personal-notify.service /etc/systemd/system/
# отредактируйте User/Group и пути в юните под своё окружение
sudo systemctl daemon-reload
sudo systemctl enable --now personal-notify
journalctl -u personal-notify -f
```

Оповещения по расписанию через cron:

```bash
crontab deploy/crontab.example   # отредактируйте путь проекта перед установкой
```

## Тесты

```bash
.venv/bin/python -m pytest
```

## Документация

- `docs/SPEC.md` — спецификация
- `docs/ARCHITECTURE.md` — архитектура и состав модулей
- `docs/TASKS.md` — план работ
