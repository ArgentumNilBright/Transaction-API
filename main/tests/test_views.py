from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from main.enums import TransactionType
from main.models import Balance, Transaction


class TransactionTests(APITestCase):
    def setUp(self):
        self.user_id = 1
        self.balance = Balance.objects.create(user_id=self.user_id, amount=Decimal('100.00'))
        self.deposit_url = reverse('deposit')
        self.withdrawal_url = reverse('withdrawal')
        self.transfer_url = reverse('transfer')
        self.balance_url = reverse('get_user_balance', args=[self.user_id])

    def test_get_user_balance(self):
        response = self.client.get(self.balance_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_id'], self.user_id)
        self.assertEqual(response.data['balance'], '100.00')
        self.assertEqual(response.data['currency'], 'RUB')

    def test_deposit(self):
        data = {
            'from_user_id': self.user_id,
            'to_user_id': self.user_id,
            'amount': '50.00',
            'operation': TransactionType.DEPOSIT.value
        }
        response = self.client.post(self.deposit_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.amount, Decimal('150.00'))
        self.assertTrue(Transaction.objects.filter(user_id=self.user_id).exists())

    def test_withdrawal_success(self):
        data = {
            'from_user_id': self.user_id,
            'to_user_id': self.user_id,
            'amount': '50.00',
            'operation': TransactionType.WITHDRAWAL.value
        }
        response = self.client.post(self.withdrawal_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.amount, Decimal('50.00'))
        self.assertTrue(Transaction.objects.filter(user_id=self.user_id).exists())

    def test_withdrawal_insufficient_funds(self):
        data = {
            'from_user_id': self.user_id,
            'to_user_id': self.user_id,
            'amount': '150.00',
            'operation': TransactionType.WITHDRAWAL.value
        }
        response = self.client.post(self.withdrawal_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_transfer_success(self):
        recipient_id = 2
        Balance.objects.create(user_id=recipient_id, amount=Decimal('0.00'))
        data = {
            'from_user_id': self.user_id,
            'to_user_id': recipient_id,
            'amount': '50.00',
            'operation': TransactionType.TRANSFER.value
        }
        response = self.client.post(self.transfer_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.balance.refresh_from_db()
        recipient_balance = Balance.objects.get(user_id=recipient_id)
        self.assertEqual(self.balance.amount, Decimal('50.00'))
        self.assertEqual(recipient_balance.amount, Decimal('50.00'))

    def test_get_balance_not_found(self):
        invalid_user_id = 999
        url = reverse('get_user_balance', args=[invalid_user_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
