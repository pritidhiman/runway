from datetime import date

from pydantic import BaseModel


class Bill(BaseModel):
    name: str
    amount: float
    due_date: date


class CreditCard(BaseModel):
    name: str
    balance: float
    apr: float
    minimum_payment: float
    due_date: date

