import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from main.enums import TransactionType
from main.models import Balance, Transaction


def process_transaction(data: dict[str, Any]) -> dict[str, Any]:
    """
    Обрабатывает транзакцию пользователей.

    Функция-оркестратор: блокирует нужные балансы, проверяет корректность данных,
    выполняет списание или зачисление средств и возвращает итоговые данные о транзакции.

    Args:
        data (dict[str, Any]): Входные данные о транзакции.

    Returns:
        dict[str, Any]: Итоговые данные о транзакции.
    """
    from_user_id = data.get('from_user_id')
    to_user_id = data.get('to_user_id')
    amount = data.get('amount')
    operation = data.get('operation')

    with transaction.atomic():
        balances = get_balances(from_user_id, to_user_id, operation)
        balance_changes = execute_transaction(balances, amount, operation)
        save_balances(balances)

        completed_at = now().strftime('%d.%m.%Y %H:%M:%S')

    return {
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'amount': amount,
        'operation': operation,
        'completed_at': completed_at,
        **balance_changes
    }


def get_balances(from_user_id: int, to_user_id: int, operation: str) -> dict[str, Balance]:
    """
    Возвращает заблокированные балансы пользователей.

    Args:
        from_user_id (int): ID пользователя, с чьего баланса списываются средства.
        to_user_id (int): ID пользователя, на чей баланс зачисляются средства.
        operation (str): Передаваемый другим микросервисом тип исполняемой операции (например, 'transfer', 'deposit' или 'withdrawal').

    Returns:
        dict[str, Balance]: Словарь, содержащий ключи 'from' и/или 'to' и соответствующие объекты балансов пользователей Balance.
    """
    balances = {}
    if operation in (TransactionType.TRANSFER.value, TransactionType.WITHDRAWAL.value):
        balances['from'] = get_object_or_404(Balance.objects.select_for_update(), user_id=from_user_id)
    if operation in (TransactionType.TRANSFER.value, TransactionType.DEPOSIT.value):
        balances['to'], _ = Balance.objects.select_for_update().get_or_create(user_id=to_user_id)

    return balances


def execute_transaction(balances: dict[str, Balance], amount: Decimal, operation: str) -> dict[str, Decimal]:
    """
    Проверяет тип транзакции, исполняет соответствующую бизнес-логику и логирует изменения баланса(ов).

    Args:
        balances (dict[str, Balance]): Словарь, содержащий ключи 'from' и/или 'to' и соответствующие объекты балансов пользователей Balance.
        amount (Decimal): Сумма денежных средств, над которой совершается транзакция.
        operation (str): Передаваемый другим микросервисом тип исполняемой операции (например, 'transfer', 'deposit' или 'withdrawal').

    Returns:
        dict[str, Decimal]: Словарь, содержащий ключи 'from_balance_before', 'from_balance_after' и/или
            'to_balance_before', 'to_balance_after' и соответствующие им значения балансов пользователей.

    Raises:
        ValidationError: Если средств для перевода недостаточно или другой микросервис передал некорректное значение operation.
    """
    balance_changes = {}

    if operation == TransactionType.TRANSFER.value:
        from_balance = balances['from']
        to_balance = balances['to']

        if from_balance.amount < amount:
            raise ValidationError({'error': 'Недостаточно средств'})

        balance_changes['from_balance_before'] = from_balance.amount
        from_balance.amount -= amount
        balance_changes['from_balance_after'] = from_balance.amount

        balance_changes['to_balance_before'] = to_balance.amount
        to_balance.amount += amount
        balance_changes['to_balance_after'] = to_balance.amount

    elif operation == TransactionType.WITHDRAWAL.value:
        from_balance = balances['from']

        if from_balance.amount < amount:
            raise ValidationError({'error': 'Недостаточно средств'})

        balance_changes['from_balance_before'] = from_balance.amount
        from_balance.amount -= amount
        balance_changes['from_balance_after'] = from_balance.amount

    elif operation == TransactionType.DEPOSIT.value:
        to_balance = balances['to']

        balance_changes['to_balance_before'] = to_balance.amount
        to_balance.amount += amount
        balance_changes['to_balance_after'] = to_balance.amount
    else:
        raise ValidationError({'error': 'Недопустимая операция'})

    return balance_changes


def save_balances(balances: dict[str, Balance]) -> None:
    """
    Сохраняет в базе данных изменения, внесённые в балансы пользователей.

    Args:
        balances (dict[str, Balance]): Словарь, содержащий ключи 'from' и/или 'to' и соответствующие объекты балансов пользователей Balance.

    Returns:
        None
    """
    for balance in balances.values():
        balance.save()


def record_transaction(data: dict[str, Any], comment: str | None = None) -> None:
    """
    Создаёт объект(ы) Transaction и сохраняет в базе данных итоговые данные об успешно завершённой транзакции.

    Args:
        data (dict[str, Any]): Итоговые данные о транзакции.
        comment (str | None): Необязательный комментарий пользователя.

    Returns:
        None
    """
    amount = data['amount']
    operation = data['operation']
    completed_at = data['completed_at']

    if 'from_balance_before' in data:
        Transaction.objects.create(
            user_id=data['from_user_id'],
            from_user_id=data['from_user_id'],
            to_user_id=data.get('to_user_id'),
            balance_before=data['from_balance_before'],
            balance_after=data['from_balance_after'],
            amount=amount,
            operation=operation,
            comment=generate_comment(operation, amount, data['from_balance_after'],
                                     completed_at, comment)
        )

    if 'to_balance_before' in data:
        Transaction.objects.create(
            user_id=data['to_user_id'],
            from_user_id=data.get('from_user_id'),
            to_user_id=data['to_user_id'],
            balance_before=data['to_balance_before'],
            balance_after=data['to_balance_after'],
            amount=amount,
            operation=operation,
            comment=generate_comment(operation, amount, data['to_balance_after'],
                                     completed_at, comment)
        )


def generate_comment(operation: str,
                     amount: Decimal,
                     balance_after: Decimal,
                     completed_at: datetime,
                     comment: str | None
                     ) -> str:
    """
    Создаёт технический комментарий к транзакции, дополняет его комментарием пользователя, если таковой передан.

    Args:
        operation (str): Передаваемый другим микросервисом тип исполняемой операции (например, 'transfer', 'deposit' или 'withdrawal').
        amount (Decimal): Сумма денежных средств, над которой совершается транзакция.
        balance_after (Decimal): Баланс денежных средств пользователя после исполнения транзакции.
        completed_at (datetime): Время завершения транзакции в формате '%d.%m.%Y %H:%M:%S'.
        comment (str | None): Необязательный комментарий пользователя.

    Returns:
        str: Итоговый комментарий к транзакции
    """
    generated_comment = (
        f'{TransactionType(operation).label} на сумму {amount}; '
        f'Баланс: {balance_after:.2f}; Время исполнения: {completed_at}'
    )

    if comment:
        generated_comment += f'; Комментарий: {comment}'

    return generated_comment
