
1. Собрать docker compose

```bash
docker compose up -d
```

2. Пересобрать телеграм бота (в случае изменения кода)

```bash
docker compose build --no-cache roadmappers_bot && docker compose up -d --force-recreate roadmappers_bot
```

```bash
docker compose up -d --build roadmappers_bot
```

