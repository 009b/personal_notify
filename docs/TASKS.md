# Задачи: personal_notify

## Фаза 0 — Проектирование
- [x] Спроектировать оповещения по расписанию (cron + CLI-задача)
- [x] Спроектировать оповещения по событиям (каркас приёма + хранилище)
- [x] Спроектировать обвязку Ollama (LLM)
- [x] Определить хранилище (интерфейс + дефолт SQLite stdlib)
- [x] Определить планировщик (системный cron)
- [x] Определить провайдера погоды (интерфейс + Gismeteo)
- [x] Обновить SPEC.md и ARCHITECTURE.md

## Фаза 1 — Базовый скелет
- [x] Настроить окружение (venv на python3.12, зависимости)
- [x] Реализовать config (загрузка `.env` + структурного конфига)
- [x] Реализовать main.py (запуск демона)
- [x] Реализовать /start, /help, /status
- [x] Whitelist-фильтр по user_id
- [x] Тесты config, handlers, access, main

## Фаза 2 — Оповещения по расписанию и погода
- [x] Интерфейс провайдера погоды + реализация Gismeteo
- [x] Обвязка Ollama (вызов модели, выбор модели, опции)
- [x] Обработка текста погодного оповещения через LLM
- [x] CLI-задача `weather` + пример строки crontab (08:00 МСК)
- [x] services/notifier (отправка в Telegram)
- [x] Тесты llm, weather, notifier, tasks
- [x] Проверка боевой отправки в Telegram (getMe + sendMessage)

## Фаза 3 — Оповещения по событиям
- [x] Интерфейс хранилища + реализация SQLite (stdlib) + фабрика
- [x] Каркас событий (EventSource, Event) + EventProcessor (дедуп → отправка)
- [x] Тесты storage и events
- [ ] Конкретные источники событий (webhook / polling) — после уточнения SPEC §8

## Фаза 4 — Деплой
- [x] systemd-сервис для демона бота (`deploy/personal-notify.service`)
- [x] crontab для задач по расписанию (`deploy/crontab.example`)
- [x] Проверка боевого прогона задачи `weather` под cron (end-to-end)
- [x] Инструкция установки в README

## Фаза 5 — Новостной дайджест
- [ ] Зависимость Telethon + секреты (`TG_API_ID`/`TG_API_HASH`/`TG_SESSION_PATH`)
- [ ] Конфиг секции `news` + промпты `news_filter`/`news_digest`
- [ ] `telegram_reader` (чтение постов каналов за окно)
- [ ] Пайплайн: collect → filter(LLM) → summarize(LLM) → format со ссылками
- [ ] CLI-задачи `news` и `news_login` + строка crontab
- [ ] Тесты (reader, pipeline, format, run_news; без сети)
- [ ] Боевой прогон + обновление README/STATUS
