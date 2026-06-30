from datetime import date

import pytest

from runway.models import Bill, CreditCard
from runway.planner import (
    calculate_plan,
    choose_debt_target,
    estimate_card_limit_risk,
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


def test_calculate_plan_only_treats_current_cycle_cash_as_extra():
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
    assert plan["cash_left_before_payday"] == -30.0
    assert plan["spendable_extra_before_payday"] == 0.0
    assert plan["next_paycheck_reserved_for_next_cycle"] == 2000.0
    assert plan["extra_after_required"] == 0.0
    assert plan["extra_to_debt"] == 0.0
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
    assert plan["cash_left_before_payday"] == 1100.0
    assert plan["spendable_extra_before_payday"] == 1100.0
    assert plan["extra_after_required"] == 1100.0
    assert plan["extra_to_savings"] == 550.0
    assert plan["extra_to_debt"] == 550.0
    assert plan["debt_target"] == "Small Balance"


def test_screenshot_case_does_not_count_next_paycheck_as_extra_cash():
    plan = calculate_plan(
        checking_balance=4100.0,
        next_paycheck_amount=4300.0,
        next_paycheck_date=date(2099, 1, 10),
        essential_spending_until_payday=300.0,
        cushion_target=100.0,
        plan_mode="Survival",
        debt_strategy="Avalanche",
        bills=[
            Bill(name="Bills", amount=3450.0, due_date=date(2099, 1, 5)),
        ],
        cards=[
            CreditCard(
                name="Cards",
                balance=5000.0,
                apr=25.0,
                minimum_payment=195.0,
                due_date=date(2099, 1, 5),
            )
        ],
    )

    assert plan["cash_left_before_payday"] == 55.0
    assert plan["spendable_extra_before_payday"] == 55.0
    assert plan["extra_to_keep_as_cash"] == 55.0
    assert plan["next_paycheck_reserved_for_next_cycle"] == 4300.0


def test_card_limit_risk_reserves_extra_payment_above_minimum():
    card = CreditCard(
        name="Close to Limit",
        balance=980.0,
        apr=24.0,
        minimum_payment=25.0,
        due_date=date(2099, 1, 5),
        credit_limit=1000.0,
        expected_new_charges_until_due=50.0,
    )

    risk = estimate_card_limit_risk(card)

    assert risk["estimated_interest"] == pytest.approx(19.60)
    assert risk["projected_balance_after_minimum"] == pytest.approx(1024.60)
    assert risk["additional_payment_needed_above_minimum"] == pytest.approx(24.60)
    assert risk["risk_level"] == "Over-limit risk"

    plan = calculate_plan(
        checking_balance=1200.0,
        next_paycheck_amount=1000.0,
        next_paycheck_date=date(2099, 1, 10),
        essential_spending_until_payday=100.0,
        cushion_target=250.0,
        plan_mode="Survival",
        debt_strategy="Avalanche",
        bills=[],
        cards=[card],
    )

    assert plan["total_minimums_due"] == 25.0
    assert plan["card_limit_safety_payments_due"] == pytest.approx(24.60)
    assert plan["required_before_payday"] == pytest.approx(399.60)
    assert plan["spendable_extra_before_payday"] == pytest.approx(800.40)
