from datetime import date

from runway.models import Bill, CreditCard
from runway.planner import (
    calculate_plan,
    choose_debt_target,
    get_cushion_target,
    get_risk_level,
)


def test_cushion_modes_use_minimums_and_percentages():
    assert get_cushion_target("Bare minimum", 1000.0, 0.0) == 100.0
    assert get_cushion_target("Bare minimum", 3000.0, 0.0) == 150.0
    assert get_cushion_target("Standard", 1000.0, 0.0) == 250.0
    assert get_cushion_target("Standard", 3000.0, 0.0) == 300.0
    assert get_cushion_target("Conservative", 1000.0, 0.0) == 500.0
    assert get_cushion_target("Conservative", 4000.0, 0.0) == 600.0
    assert get_cushion_target("Custom", 1000.0, 425.0) == 425.0


def test_risk_level_thresholds():
    assert get_risk_level(-1.0, -1.0) == "Red"
    assert get_risk_level(100.0, 19.99) == "Yellow"
    assert get_risk_level(100.0, 20.0) == "Green"


def test_choose_debt_target_by_avalanche_or_snowball():
    cards = [
        CreditCard(
            name="High APR",
            balance=2000.0,
            apr=29.99,
            minimum_payment=80.0,
            due_date=date(2099, 1, 5),
        ),
        CreditCard(
            name="Small Balance",
            balance=500.0,
            apr=19.99,
            minimum_payment=25.0,
            due_date=date(2099, 1, 6),
        ),
    ]

    assert choose_debt_target(cards, "Avalanche").name == "High APR"
    assert choose_debt_target(cards, "Snowball").name == "Small Balance"
    assert choose_debt_target([], "Avalanche") is None


def test_calculate_plan_preserves_existing_paydown_behavior():
    bills = [
        Bill(name="Rent", amount=500.0, due_date=date(2099, 1, 5)),
        Bill(name="Later bill", amount=999.0, due_date=date(2099, 2, 1)),
    ]
    cards = [
        CreditCard(
            name="High APR",
            balance=2000.0,
            apr=29.99,
            minimum_payment=80.0,
            due_date=date(2099, 1, 5),
        ),
        CreditCard(
            name="Later card",
            balance=300.0,
            apr=12.99,
            minimum_payment=30.0,
            due_date=date(2099, 2, 1),
        ),
    ]

    plan = calculate_plan(
        checking_balance=1000.0,
        next_paycheck_amount=2000.0,
        next_paycheck_date=date(2099, 1, 10),
        essential_spending_until_payday=200.0,
        cushion_target=250.0,
        plan_mode="Paydown",
        debt_strategy="Avalanche",
        bills=bills,
        cards=cards,
    )

    assert plan["total_bills_due"] == 500.0
    assert plan["total_minimums_due"] == 80.0
    assert plan["required_before_payday"] == 1030.0
    assert plan["runway_after_required"] == -30.0
    assert plan["risk_level"] == "Red"
    assert plan["cash_after_paycheck"] == 3000.0
    assert plan["extra_after_required"] == 1970.0
    assert plan["extra_to_debt"] == 1970.0
    assert plan["extra_to_savings"] == 0.0
    assert plan["extra_to_keep_as_cash"] == 0.0
    assert plan["debt_target"] == "High APR"


def test_calculate_plan_splits_balanced_extra_cash():
    plan = calculate_plan(
        checking_balance=1500.0,
        next_paycheck_amount=1000.0,
        next_paycheck_date=date(2099, 1, 10),
        essential_spending_until_payday=100.0,
        cushion_target=250.0,
        plan_mode="Balanced",
        debt_strategy="Snowball",
        bills=[],
        cards=[
            CreditCard(
                name="Small Balance",
                balance=400.0,
                apr=20.0,
                minimum_payment=50.0,
                due_date=date(2099, 1, 5),
            )
        ],
    )

    assert plan["required_before_payday"] == 400.0
    assert plan["extra_after_required"] == 2100.0
    assert plan["extra_to_savings"] == 1050.0
    assert plan["extra_to_debt"] == 1050.0
    assert plan["debt_target"] == "Small Balance"

