from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, APIException
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from main.enums import TransactionType
from main.models import Balance, Transaction
from main.serializers import TransactionSerializer, UserTransactionsListSerializer
from main.services.transaction_service import process_transaction, record_transaction


class BaseTransactionAPIView(APIView):
    """
    Базовый класс представления, реализующий общую логику обработки всех типов транзакций.

    Attributes:
        OPERATION_TYPE (str | None): Тип исполняемой транзакции. Наследуется и устанавливается дочерними классами.
    """
    OPERATION_TYPE = None
    serializer_class = TransactionSerializer

    def post(self, request: Request) -> Response:
        """
        Принимает POST-запрос клиента.

        Вызывает метод обработки POST-запроса, выполняет проверку на соответствие типа исполняемой операции и эндпоинта, возвращает объект Response.

        Args:
            request (Request): POST-запрос клиента.

        Returns:
            Response: ответ сервера на запрос клиента.
        """
        if request.data.get('operation') != self.OPERATION_TYPE:
            raise ValidationError({'error': f'Недопустимая операция для transactions/{self.OPERATION_TYPE}/'})

        return self.handle_transaction(request)

    def handle_transaction(self, request: Request) -> Response:
        """
        Обрабатывает POST-запрос.

        Выполняет транзакцию с использованием сериализованных и валидированных входных данных, возвращает объект Response.

        Args:
            request (Request): POST-запрос клиента.

        Returns:
            Response: ответ сервера на запрос клиента.
        """
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transaction_data = process_transaction(serializer.validated_data)

        comment = serializer.validated_data.get('comment')
        record_transaction(transaction_data, comment)

        balance_after = self.get_balance_after(transaction_data)

        return Response(
            {
                'detail': 'Операция успешно выполнена',
                'balance': f'{balance_after:.2f}',
                'completed_at': transaction_data['completed_at']
            },
            status=status.HTTP_200_OK
        )

    def get_balance_after(self, transaction_data: dict[str, Any]) -> Decimal:
        """
        Возвращает баланс денежных средств пользователя после исполнения транзакции.

        Args:
            transaction_data (dict[str, Any]): Итоговые данные о транзакции.

        Returns:
            Decimal: Баланс денежных средств пользователя после исполнения транзакции.
        """
        operation = transaction_data['operation']
        if operation in (TransactionType.WITHDRAWAL.value, TransactionType.TRANSFER.value):
            balance_after = transaction_data['from_balance_after']
        else:  # deposit
            balance_after = transaction_data['to_balance_after']

        return balance_after


class DepositAPIView(BaseTransactionAPIView):
    """
    Дочерний класс BaseTransactionAPIView, отвечающий за обработку запросов на /transactions/deposit/

    Attributes:
        OPERATION_TYPE (Literal['deposit']): Тип исполняемой транзакции.
    """
    OPERATION_TYPE = TransactionType.DEPOSIT.value


class WithdrawalAPIView(BaseTransactionAPIView):
    """
    Дочерний класс BaseTransactionAPIView, отвечающий за обработку запросов на /transactions/withdrawal/

    Attributes:
        OPERATION_TYPE (Literal['withdrawal']): Тип исполняемой транзакции.
    """
    OPERATION_TYPE = TransactionType.WITHDRAWAL.value


class TransferAPIView(BaseTransactionAPIView):
    """
    Дочерний класс BaseTransactionAPIView, отвечающий за обработку запросов на /transactions/transfer/

    Attributes:
        OPERATION_TYPE (Literal['transfer']): Тип исполняемой транзакции.
    """
    OPERATION_TYPE = TransactionType.TRANSFER.value


class GetUserBalanceAPIView(APIView):
    """
    Класс, предоставляющий метод получения баланса денежных средств пользователя по ID
    """

    def get(self, request: Request, user_id: int) -> Response:
        """
        Принимает GET-запрос клиента.

        Вызывает метод получения баланса пользователя из базы данных. В случае, если в параметрах запроса передана валюта,
        конвертирует полученное значение в эту валюту согласно кэшированной таблице курсов, предоставляемой сторонним API.

        Args:
            request (Request): GET-запрос клиента.
            user_id (int): ID пользователя, чей баланс необходимо вернуть.

        Returns:
            Response: ответ сервера на запрос клиента.
        """
        balance = self.get_balance(user_id)
        currency = self.request.query_params.get('currency', 'RUB').upper()

        if currency != 'RUB':
            rate = self.get_exchange_rate(currency)
            converted_balance = Decimal(balance) * Decimal(rate)
        else:
            converted_balance = balance

        return Response(
            {
                'user_id': user_id,
                'balance': f'{converted_balance:.2f}',
                'currency': currency
            },
            status=status.HTTP_200_OK
        )

    def get_balance(self, user_id: int) -> Decimal:
        """
        Получает баланс пользователя из базы данных по его ID.

        Args:
            user_id (int): ID пользователя, чей баланс необходимо вернуть.

        Returns:
            Decimal: Баланс денежных средств пользователя.

        Raises:
            NotFound: В случае, если указанному user_id не соответствует ни один объект Balance.
        """
        try:
            balance = Balance.objects.get(user_id=user_id)
        except Balance.DoesNotExist:
            raise NotFound({'error': 'Баланс пользователя не найден'})

        return balance.amount

    def get_exchange_rate(self, currency: str) -> float:
        """
        Возвращает курс обмена валют из кэшированного словаря.

        Args:
            currency (str): Наименование валюты. Например, 'USD', 'CNY', 'JPY'.

        Returns:
            float: извлечённое значение курса обмена.

        Raises:
            APIException: В случае, если не удалось получить кэшированные данные о курсах валют.
            ValidationError: В случае, если переданное наименование валюты не было найдено в кэшированном ответе стороннего API.
        """
        data = cache.get('exchange_rates')
        if data is None:
            raise APIException({'error': 'Данные о курсах валют временно недоступны'})

        try:
            rate = data['conversion_rates'][currency]
        except KeyError:
            raise ValidationError({'error': f'Валюта {currency} не найдена в ответе API'})

        return rate


class GetUserTransactionsAPIView(ListAPIView):
    """
    Класс, предоставляющий метод получения пагинированного списка транзакций пользователя по его ID.
    """
    serializer_class = UserTransactionsListSerializer
    pagination_class = PageNumberPagination
    queryset = Transaction.objects.all()

    def get_queryset(self) -> QuerySet:
        """
        Возвращает кверисет экземпляров класса модели Transaction.

        Кверисет содержит все транзакции пользователя с ID, переданным в параметре запроса user_id.
        Сортирует результирующий кверисет по указанному в параметре запроса 'ordering' полю. По умолчанию - по убыванию даты.

        Returns:
            QuerySet: Отсортированный результирующий кверисет.

        Raises:
            ValidationError: В случае, если указанному user_id не соответствует ни один объект Transaction.
        """
        user_id = self.kwargs.get('user_id')
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = self.queryset.filter(user_id=user_id).order_by(ordering)
        if not queryset:
            raise ValidationError({'error': 'Транзакции пользователя не найдены'})

        return queryset
