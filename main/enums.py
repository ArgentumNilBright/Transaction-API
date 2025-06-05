from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'

    @property
    def label(self) -> str:
        return {
            self.DEPOSIT: 'Зачисление',
            self.WITHDRAWAL: 'Списание',
            self.TRANSFER: 'Перевод',
        }[self]
