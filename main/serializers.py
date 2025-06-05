from decimal import Decimal
from typing import Any

from rest_framework import serializers

from main.enums import TransactionType
from main.models import Transaction


class TransactionSerializer(serializers.Serializer):
    """
    Сериализатор, обрабатывающий входные данные транзакции.
    """
    from_user_id = serializers.IntegerField(required=False)
    to_user_id = serializers.IntegerField(required=False)
    operation = serializers.ChoiceField(choices=[(t.value, t.label) for t in TransactionType])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1024)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        operation = data.get('operation')

        if operation == 'deposit':
            if 'to_user_id' not in data:
                raise serializers.ValidationError({'to_user_id': 'Это поле обязательно для зачисления'})

        elif operation == 'withdrawal':
            if 'from_user_id' not in data:
                raise serializers.ValidationError({'from_user_id': 'Это поле обязательно для списания'})

        elif operation == 'transfer':
            if 'from_user_id' not in data or 'to_user_id' not in data:
                raise serializers.ValidationError(
                    {'error': 'Для перевода необходимо указать from_user_id и to_user_id'})
            if data['from_user_id'] == data['to_user_id']:
                raise serializers.ValidationError({'error': 'Нельзя переводить средства самому себе'})
        else:
            raise serializers.ValidationError({'error': 'Недопустимая операция'})

        return data


class UserTransactionsListSerializer(serializers.ModelSerializer):
    """
    Сериализатор, применяемый при отображении списка транзакций пользователя.
    """

    class Meta:
        model = Transaction
        fields = '__all__'
