from datetime import date
from typing import Optional

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
    credit_limit: Optional[float] = None
    expected_new_charges_until_due: float = 0.0
