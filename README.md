# User Balance Management API

Веб-приложение для управления транзакциями и балансами пользователей. Реализует пополнение баланса, снятие средств,
переводы между пользователями и отображение баланса в любой валюте. Проект использует Docker и Docker Compose для
лёгкого развертывания.

---

## Возможности

- Пополнение баланса
- Снятие средств
- Перевод между пользователями
- Автоматическая запись истории транзакций каждого пользователя
- Получение списка всех транзакций пользователя
- Получение текущего баланса в указанной валюте (по умолчанию RUB)
- Кэширование курсов валют с помощью Redis
- Автоматическая генерация документации API через drf-spectacular

---

## Установка и запуск через Docker

1. Клонируйте репозиторий:

```commandline
git clone https://github.com/ArgentumNilBright/Transaction-API.git
cd Transaction-API
```

2. Скопируйте .env.example в .env и заполните его своими данными

```commandline
copy .env.example .env
```

3. Постройте и запустите контейнеры:

```commandline
docker-compose up --build
```

4. Приложение будет доступно по адресу:

```commandline
http://localhost:8000/
```

---

## Пример использования API

### Зачисление:

```commandline
POST /api/v1/transactions/deposit/
{
    "operation": "deposit",
    "amount": 100.00,
    "to_user_id": 1,
    "comment": "example_comment"
}
```

### Списание:

```commandline
POST /api/v1/transactions/withdrawal/
{
    "operation": "withdrawal",
    "amount": 50.00,
    "from_user_id": 1,
    "comment": "example_comment"
}
```

### Перевод:

```commandline
POST /api/v1/transactions/transfer/
{
    "operation": "transfer",
    "amount": 25.00,
    "from_user_id": 1,
    "to_user_id": 2,
    "comment": "example_comment"
}
```

### Получение баланса пользователя:

```commandline
GET api/v1/users/1/balance/?currency=CNY
```

### Получение списка транзакций пользователя:

```commandline
GET api/v1/users/1/transactions/
```