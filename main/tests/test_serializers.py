from decimal import Decimal

from django.test import TestCase

from main.enums import TransactionType
from main.models import Transaction
from main.serializers import TransactionSerializer, UserTransactionsListSerializer


class TransactionSerializerTests(TestCase):
    def test_valid_data(self):
        data = {
            'from_user_id': 1,
            'to_user_id': 2,
            'amount': '100.00',
            'operation': TransactionType.TRANSFER.value,
            'comment': 'Test'
        }
        serializer = TransactionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['from_user_id'], 1)
        self.assertEqual(validated_data['to_user_id'], 2)
        self.assertEqual(validated_data['amount'], Decimal('100.00'))
        self.assertEqual(validated_data['operation'], TransactionType.TRANSFER.value)
        self.assertEqual(validated_data['comment'], 'Test')

    def test_missing_required_field(self):
        data = {
            'from_user_id': 1,
            'amount': '100.00',
            'operation': TransactionType.DEPOSIT.value
        }
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('to_user_id', serializer.errors)

    def test_invalid_amount(self):
        data = {
            'from_user_id': 1,
            'to_user_id': 2,
            'amount': '-50.00',
            'operation': TransactionType.TRANSFER.value
        }
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class UserTransactionsListSerializerTests(TestCase):
    def setUp(self):
        self.transaction = Transaction.objects.create(
            user_id=1,
            from_user_id=1,
            to_user_id=2,
            balance_before=Decimal('100.00'),
            balance_after=Decimal('80.00'),
            amount=Decimal('20.00'),
            operation=TransactionType.TRANSFER.value,
            comment='Test transfer'
        )

    def test_serialization(self):
        serializer = UserTransactionsListSerializer(instance=self.transaction)
        data = serializer.data
        self.assertEqual(data['user_id'], 1)
        self.assertEqual(data['from_user_id'], 1)
        self.assertEqual(data['to_user_id'], 2)
        self.assertEqual(Decimal(data['balance_before']), Decimal('100.00'))
        self.assertEqual(Decimal(data['balance_after']), Decimal('80.00'))
        self.assertEqual(Decimal(data['amount']), Decimal('20.00'))
        self.assertEqual(data['operation'], TransactionType.TRANSFER.value)
        self.assertEqual(data['comment'], 'Test transfer')
