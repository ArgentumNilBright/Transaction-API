from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from main.enums import TransactionType


class Balance(models.Model):
    user_id = models.IntegerField(unique=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )


class Transaction(models.Model):
    user_id = models.IntegerField()
    from_user_id = models.IntegerField(null=True, blank=True)
    to_user_id = models.IntegerField(null=True, blank=True)
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    operation = models.CharField(max_length=20, choices=[(t.value, t.label) for t in TransactionType])
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, max_length=1024)
