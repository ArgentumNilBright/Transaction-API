from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from main.enums import TransactionType
from main.models import Balance, Transaction
from main.services.transaction_service import (
    process_transaction,
    get_balances,
    execute_transaction,
    save_balances,
    record_transaction
)


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.from_user = Balance.objects.create(user_id=1, amount=Decimal('100.00'))
        self.to_user = Balance.objects.create(user_id=2, amount=Decimal('50.00'))

    def test_get_balances_transfer(self):
        balances = get_balances(1, 2, TransactionType.TRANSFER.value)
        self.assertEqual(balances['from'], self.from_user)
        self.assertEqual(balances['to'], self.to_user)

    def test_get_balances_withdrawal(self):
        balances = get_balances(1, None, TransactionType.WITHDRAWAL.value)
        self.assertEqual(balances['from'], self.from_user)
        self.assertNotIn('to', balances)

    def test_get_balances_deposit(self):
        balances = get_balances(None, 2, TransactionType.DEPOSIT.value)
        self.assertEqual(balances['to'], self.to_user)
        self.assertNotIn('from', balances)

    def test_execute_transaction_transfer_success(self):
        balances = {'from': self.from_user, 'to': self.to_user}
        result = execute_transaction(balances, Decimal('30.00'), TransactionType.TRANSFER.value)
        self.assertEqual(result['from_balance_after'], Decimal('70.00'))
        self.assertEqual(result['to_balance_after'], Decimal('80.00'))

    def test_execute_transaction_transfer_insufficient_funds(self):
        balances = {'from': self.from_user, 'to': self.to_user}
        with self.assertRaises(ValidationError) as context:
            execute_transaction(balances, Decimal('200.00'), TransactionType.TRANSFER.value)
        self.assertIn('Недостаточно средств', str(context.exception))

    def test_execute_transaction_withdrawal_success(self):
        balances = {'from': self.from_user}
        result = execute_transaction(balances, Decimal('50.00'), TransactionType.WITHDRAWAL.value)
        self.assertEqual(result['from_balance_after'], Decimal('50.00'))

    def test_execute_transaction_withdrawal_insufficient_funds(self):
        balances = {'from': self.from_user}
        with self.assertRaises(ValidationError):
            execute_transaction(balances, Decimal('200.00'), TransactionType.WITHDRAWAL.value)

    def test_execute_transaction_deposit_success(self):
        balances = {'to': self.to_user}
        result = execute_transaction(balances, Decimal('30.00'), TransactionType.DEPOSIT.value)
        self.assertEqual(result['to_balance_after'], Decimal('80.00'))

    def test_save_balances(self):
        balances = {'from': self.from_user, 'to': self.to_user}
        balances['from'].amount -= Decimal('10.00')
        balances['to'].amount += Decimal('10.00')
        save_balances(balances)
        self.assertEqual(Balance.objects.get(user_id=1).amount, Decimal('90.00'))
        self.assertEqual(Balance.objects.get(user_id=2).amount, Decimal('60.00'))

    def test_process_transaction_transfer(self):
        data = {
            'from_user_id': 1,
            'to_user_id': 2,
            'amount': Decimal('20.00'),
            'operation': TransactionType.TRANSFER.value
        }
        result = process_transaction(data)
        self.assertEqual(result['from_balance_after'], Decimal('80.00'))
        self.assertEqual(result['to_balance_after'], Decimal('70.00'))

    def test_record_transaction_creates_transactions(self):
        data = {
            'amount': Decimal('20.00'),
            'operation': TransactionType.TRANSFER.value,
            'completed_at': '01.01.2025 12:00:00',
            'from_user_id': 1,
            'to_user_id': 2,
            'from_balance_before': Decimal('100.00'),
            'from_balance_after': Decimal('80.00'),
            'to_balance_before': Decimal('50.00'),
            'to_balance_after': Decimal('70.00')
        }
        record_transaction(data, comment="Test")
        transactions = Transaction.objects.filter(user_id__in=[1, 2])
        self.assertEqual(transactions.count(), 2)
