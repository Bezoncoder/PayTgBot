# Alembic


Убедись, что перед первым стартом удалены папка `migration` и файл `alembic.ini`

Установить библиотеки из `telegram_bot/requirements.txt`

Если ругается на urllib3, то можно использовать обход
```bash
pip install -r requirements.txt --break-system-packages --ignore-installed urllib3
```

Для начала работы с Alembic,
нам нужно выполнить его инициализацию с поддержкой асинхронного взаимодействия с базой данных.

Это можно сделать с помощью следующей команды:
```bash
alembic init -t async migration
```
***

### Настройка migration/env.py для работы с базой данных

1. Импорт подключения и моделей
```bash
from db.database import Base, DATABASE_URL
from db.models import *
```
2. Конфигурация подключения
```bash
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
```
3. Заменить `target_metadata = None` на `target_metadata = Base.metadata`
```bash
target_metadata = Base.metadata
```
***
### Подготовка файла миграций

Эта команда создаст миграционный файл,
который Alembic будет использовать для создания наших таблиц на основе моделей.
```bash
alembic revision --autogenerate -m "Initial revision"
```
Создаст Инструкции в файле:

migration\versions\a59042faf165_initial_revision.py

Для того чтобы обновить базу данных до последней версии, выполните команду:
```bash
alembic upgrade head
```
Выполнение миграции до конкретного ID
```bash
alembic upgrade d97a9824423b
```
В данном случае d97a9824423b — это уникальный идентификатор нужной миграции.

Alembic выполнит все миграции до указанного ID, обновив базу данных до состояния,
соответствующего этой версии.

***
### Откат миграций: Downgrade

Откат на одну версию назад
Чтобы откатить миграцию на одну версию назад, используйте следующую команду:
```bash
alembic downgrade -1
```
Откат до конкретной миграции
```bash
alembic downgrade d97a9824423b
```
Эта команда вернет базу данных к состоянию, соответствующему миграции с ID d97a9824423b,
и удалит все изменения, примененные после нее.

***
### UPGRADE

Создадим файл с миграциями и применим миграцию.
```bash
alembic revision --autogenerate -m "update tables"
```

```bash
alembic upgrade head
```


