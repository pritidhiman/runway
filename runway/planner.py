from datetime import date
from typing import List, Optional

from runway.models import Bill, CreditCard


def days_until(target_date: date) -> int:
    return max((target_date - date.today()).days, 1)


def get_cushion_target(
    cushion_mode: str,
    checking_balance: float,
    custom_cushion: float,
) -> float:
    if cushion_mode == "Bare minimum":
        return max(100.0, checking_balance * 0.05)

    if cushion_mode == "Standard":
        return max(250.0, checking_balance * 0.10)

    if cushion_mode == "Conservative":
        return max(500.0, checking_balance * 0.15)

    return custom_cushion


def get_risk_level(runway_after_required: float, safe_daily_spend: float) -> str:
    if runway_after_required < 0:
        return "Red"

    if safe_daily_spend < 20:
        return "Yellow"

    return "Green"


def choose_debt_target(
    cards: List[CreditCard],
    debt_strategy: str,
) -> Optional[CreditCard]:
    if not cards:
        return None

    if debt_strategy == "Avalanche":
        return max(cards, key=lambda card: card.apr)

    if debt_strategy == "Snowball":
        return min(cards, key=lambda card: card.balance)

    return None


def calculate_plan(
    checking_balance: float,
    next_paycheck_amount: float,
    next_paycheck_date: date,
    essential_spending_until_payday: float,
    cushion_target: float,
    plan_mode: str,
    debt_strategy: str,
    bills: List[Bill],
    cards: List[CreditCard],
):
    days_to_paycheck = days_until(next_paycheck_date)

    upcoming_bills = [
        bill for bill in bills
        if bill.due_date <= next_paycheck_date
    ]

    upcoming_card_minimums = [
        card for card in cards
        if card.due_date <= next_paycheck_date
    ]

    total_bills_due = sum(bill.amount for bill in upcoming_bills)
    total_minimums_due = sum(card.minimum_payment for card in upcoming_card_minimums)

    required_before_payday = (
        total_bills_due
        + total_minimums_due
        + essential_spending_until_payday
        + cushion_target
    )

    runway_after_required = checking_balance - required_before_payday
    safe_daily_spend = runway_after_required / days_to_paycheck
    risk_level = get_risk_level(runway_after_required, safe_daily_spend)

    cash_after_paycheck = checking_balance + next_paycheck_amount
    extra_after_required = cash_after_paycheck - required_before_payday

    debt_target = choose_debt_target(cards, debt_strategy)

    extra_to_debt = 0.0
    extra_to_savings = 0.0
    extra_to_keep_as_cash = 0.0

    if extra_after_required > 0:
        if plan_mode == "Survival":
            extra_to_keep_as_cash = extra_after_required

        elif plan_mode == "Paydown":
            extra_to_debt = extra_after_required

        elif plan_mode == "Balanced":
            extra_to_savings = extra_after_required * 0.50
            extra_to_debt = extra_after_required * 0.50

    paycheck_allocation = {
        "Starting checking balance": checking_balance,
        "Next paycheck": next_paycheck_amount,
        "Bills due": total_bills_due,
        "Credit card minimums": total_minimums_due,
        "Essential spending": essential_spending_until_payday,
        "Cash cushion": cushion_target,
        "Extra kept as cash": extra_to_keep_as_cash,
        "Extra to savings": extra_to_savings,
        "Extra to debt": extra_to_debt,
    }

    recommendations = []

    if risk_level == "Red":
        recommendations.append(
            "Crisis mode: you are short before payday with the current plan."
        )
        recommendations.append(
            "Prioritize housing, utilities, food, transportation, medicine, pets, and credit card minimums. Do not make extra debt payments yet."
        )

    elif risk_level == "Yellow":
        recommendations.append(
            "You can make it to payday, but cash flow is tight. One unexpected expense could break the plan."
        )

    else:
        recommendations.append(
            "You can make it to payday with your cushion protected."
        )

    if extra_after_required <= 0:
        recommendations.append(
            "After your next paycheck, there is no extra cash available beyond required expenses and your cushion."
        )
    else:
        if plan_mode == "Survival":
            recommendations.append(
                f"Survival mode: keep the extra ${extra_after_required:,.2f} as cash instead of making extra debt payments."
            )

        elif plan_mode == "Balanced":
            recommendations.append(
                f"Balanced mode: put ${extra_to_savings:,.2f} toward savings/cash cushion and ${extra_to_debt:,.2f} toward debt."
            )

        elif plan_mode == "Paydown":
            if debt_target:
                recommendations.append(
                    f"Paydown mode: put the extra ${extra_to_debt:,.2f} toward {debt_target.name}."
                )
            else:
                recommendations.append(
                    "Paydown mode selected, but no credit cards were entered."
                )

    if debt_target and extra_to_debt > 0:
        if debt_strategy == "Avalanche":
            recommendations.append(
                f"{debt_target.name} is the recommended target because it has the highest APR at {debt_target.apr:.2f}%."
            )
        elif debt_strategy == "Snowball":
            recommendations.append(
                f"{debt_target.name} is the recommended target because it has the smallest balance at ${debt_target.balance:,.2f}."
            )

    return {
        "days_to_paycheck": days_to_paycheck,
        "total_bills_due": total_bills_due,
        "total_minimums_due": total_minimums_due,
        "essential_spending": essential_spending_until_payday,
        "cushion_target": cushion_target,
        "required_before_payday": required_before_payday,
        "runway_after_required": runway_after_required,
        "safe_daily_spend": safe_daily_spend,
        "risk_level": risk_level,
        "next_paycheck_amount": next_paycheck_amount,
        "cash_after_paycheck": cash_after_paycheck,
        "extra_after_required": extra_after_required,
        "paycheck_allocation": paycheck_allocation,
        "debt_target": debt_target.name if debt_target else None,
        "extra_to_debt": extra_to_debt,
        "extra_to_savings": extra_to_savings,
        "extra_to_keep_as_cash": extra_to_keep_as_cash,
        "recommendations": recommendations,
    }

