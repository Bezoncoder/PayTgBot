# Platega.

> Менеджер: [t.me/Platega_milena](https://t.me/Platega_milena)

> 📑 **API** — [docs.platega.io](https://docs.platega.io/)  
> 📰 **Новости** — [t.me/plategaio](https://t.me/plategaio)  
> ☝️ **Кабинет** — [platega.io](https://platega.io/)

> 🔐 **Login:** 
>```
>chiksleadmodels@gmail.com
>```

> 🔑 **Password:** 
>```
>Bezoncoder_1986
>```

> **Профиль**

> 🔐 **ID мерчанта:** 
> ```
> a8e1a6ed-c586-478b-ac3d-81ac1eb70cf5
> ```
> ⚙️ **API Key:**
> ```
> 9kx7SgS9BYfP07Pq0ExsVqExYZHXGLvGKVEhMLXx5kzgVmTGLFqC53NkgOaB3UdNhturqAwumz3D1kjPWpOMJYuS1TDBDhwOVStk
> ```
# Запуск docker с PostgreSQl

Креды доступа:

    Хост: localhost
    Порт: 5432
    БД: botdb
    Пользователь: botuser
    Пароль: bezoncoder_1986

1. Перейти в папку проекта
```
cd PayTgbot
```
2. Запустить PostgreSQL (фоново)
```
docker-compose up -d
```
3. Проверить статус
```
docker-compose ps
```
4. Посмотреть логи
```
docker compose logs postgres
```
5. Подключиться к БД
```
docker compose exec postgres psql -U botuser -d botdb
```
# Запуск Бота

🔍 Проверить работу:
```
sudo systemctl status paybot
```
Логи в реальном времени
```
sudo journalctl -u paybot -f
```
Последние 20 строк + следить за новыми
```
journalctl -u paybot -n 20 -f
```


1. Создать файл
```
sudo nano /etc/systemd/system/paybot.service
```
2. Вставить содержимое (замени пути/имена)
```
[Unit]
Description=PayTgbot Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/paytgbot/PayTgBot/telegram_bot
Environment="BOT_TOKEN=8755324327:AAHqmo5yC3SdNkWR6BBHmShlavAegKhCZYg"
Environment="USER=sBcdl7KQt9"
Environment="PASSWORD=8Dgwr0u6Cw"
Environment="DB_HOST=localhost"
Environment="DB_PORT=5432"
Environment="DB_NAME=botdb"
Environment="DB_USER=botuser"
Environment="DB_PASSWORD=bezoncoder_1986"
Environment="TECH_CHANNEL=-1003818704021"
Environment="MERCHANT_ID=a8e1a6ed-c586-478b-ac3d-81ac1eb70cf5"
Environment="YOOMONEY_TOKEN=4100118525733090.CF5E9E494184C19E00CBF6BE3948D83D6DFD7DBEB0E5ACB1647C4A683F9B39B2D5C60E06A4F6DB66C75C8BDBA0808E03F943DAB985D98A57C0D2624A5D279BC80D8F132F6DE28DDABE46C54C550BE78003F7D2CA076475A1368ABF05E59A2C970363D2CE29A736F4DC73FDB46DE1F82B8EEDB7A091BAAA47F4BE1E14B66EE1A8"
Environment="PLATEGA_SECRET_KEY=9kx7SgS9BYfP07Pq0ExsVqExYZHXGLvGKVEhMLXx5kzgVmTGLFqC53NkgOaB3UdNhturqAwumz3D1kjPWpOMJYuS1TDBDhwOVStk"
Environment="URL=https://155.212.228.65"
ExecStart=/root/paytgbot/PayTgBot/telegram_bot/venv/bin/python paybot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
3. Перезагрузить systemd
```
sudo systemctl daemon-reload
```
4. Запустить
```
sudo systemctl start paybot
```
5. Добавить в автозагрузку
```
sudo systemctl enable paybot
```
