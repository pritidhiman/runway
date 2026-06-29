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


def estimate_card_limit_risk(card: CreditCard) -> Optional[dict]:
    if card.credit_limit is None or card.credit_limit <= 0:
        return None

    estimated_interest = card.balance * (card.apr / 100) / 12
    projected_balance_after_minimum = (
        card.balance
        + estimated_interest
        + card.expected_new_charges_until_due
        - card.minimum_payment
    )
    available_credit_after_minimum = (
        card.credit_limit - projected_balance_after_minimum
    )
    projected_utilization = (
        projected_balance_after_minimum / card.credit_limit
    )
    payment_needed_to_stay_under_limit = max(
        card.balance
        + estimated_interest
        + card.expected_new_charges_until_due
        - card.credit_limit,
        0.0,
    )
    additional_payment_needed_above_minimum = max(
        payment_needed_to_stay_under_limit - card.minimum_payment,
        0.0,
    )

    if additional_payment_needed_above_minimum > 0:
        risk_level = "Over-limit risk"
    elif projected_utilization >= 0.90:
        risk_level = "Near limit"
    else:
        risk_level = "OK"

    return {
        "card_name": card.name,
        "credit_limit": card.credit_limit,
        "estimated_interest": estimated_interest,
        "expected_new_charges_until_due": card.expected_new_charges_until_due,
        "projected_balance_after_minimum": projected_balance_after_minimum,
        "available_credit_after_minimum": available_credit_after_minimum,
        "projected_utilization": projected_utilization,
        "payment_needed_to_stay_under_limit": payment_needed_to_stay_under_limit,
        "additional_payment_needed_above_minimum": (
            additional_payment_needed_above_minimum
        ),
        "risk_level": risk_level,
    }


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
    card_limit_risks = [
        risk for risk in (
            estimate_card_limit_risk(card) for card in upcoming_card_minimums
        )
        if risk is not None
    ]
    card_limit_safety_payments_due = sum(
        risk["additional_payment_needed_above_minimum"]
        for risk in card_limit_risks
    )

    required_before_payday = (
        total_bills_due
        + total_minimums_due
        + card_limit_safety_payments_due
        + essential_spending_until_payday
        + cushion_target
    )

    runway_after_required = checking_balance - required_before_payday
    safe_daily_spend = runway_after_required / days_to_paycheck
    risk_level = get_risk_level(runway_after_required, safe_daily_spend)

    cash_after_paycheck = checking_balance + next_paycheck_amount
    cash_left_before_payday = runway_after_required
    spendable_extra_before_payday = max(cash_left_before_payday, 0.0)
    next_paycheck_reserved_for_next_cycle = next_paycheck_amount

    debt_target = choose_debt_target(cards, debt_strategy)

    extra_to_debt = 0.0
    extra_to_savings = 0.0
    extra_to_keep_as_cash = 0.0

    if spendable_extra_before_payday > 0:
        if plan_mode == "Survival":
            extra_to_keep_as_cash = spendable_extra_before_payday

        elif plan_mode == "Paydown":
            extra_to_debt = spendable_extra_before_payday

        elif plan_mode == "Balanced":
            extra_to_savings = spendable_extra_before_payday * 0.50
            extra_to_debt = spendable_extra_before_payday * 0.50

    paycheck_allocation = {
        "Starting checking balance": checking_balance,
        "Bills due before payday": total_bills_due,
        "Credit card minimums before payday": total_minimums_due,
        "Extra card limit protection": card_limit_safety_payments_due,
        "Essential spending before payday": essential_spending_until_payday,
        "Cash cushion protected": cushion_target,
        "Cash left before payday": cash_left_before_payday,
        "Next paycheck reserved for next cycle": next_paycheck_reserved_for_next_cycle,
        "Current-cycle extra kept as cash": extra_to_keep_as_cash,
        "Current-cycle extra to savings": extra_to_savings,
        "Current-cycle extra to debt": extra_to_debt,
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

    if spendable_extra_before_payday <= 0:
        recommendations.append(
            "There is no current-cycle extra cash available beyond required expenses and your cushion."
        )
    else:
        if plan_mode == "Survival":
            recommendations.append(
                f"Survival mode: keep the current-cycle extra ${spendable_extra_before_payday:,.2f} as cash instead of making extra debt payments."
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

    for risk in card_limit_risks:
        if risk["additional_payment_needed_above_minimum"] > 0:
            recommendations.append(
                f"{risk['card_name']} may need an extra ${risk['additional_payment_needed_above_minimum']:,.2f} above the minimum payment to avoid going over the credit limit."
            )
        elif risk["risk_level"] == "Near limit":
            recommendations.append(
                f"{risk['card_name']} is projected to stay under its limit after the minimum payment, but utilization would still be about {risk['projected_utilization'] * 100:.1f}%."
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
        "card_limit_risks": card_limit_risks,
        "card_limit_safety_payments_due": card_limit_safety_payments_due,
        "essential_spending": essential_spending_until_payday,
        "cushion_target": cushion_target,
        "required_before_payday": required_before_payday,
        "runway_after_required": runway_after_required,
        "safe_daily_spend": safe_daily_spend,
        "risk_level": risk_level,
        "next_paycheck_amount": next_paycheck_amount,
        "cash_after_paycheck": cash_after_paycheck,
        "cash_left_before_payday": cash_left_before_payday,
        "spendable_extra_before_payday": spendable_extra_before_payday,
        "next_paycheck_reserved_for_next_cycle": next_paycheck_reserved_for_next_cycle,
        "extra_after_required": spendable_extra_before_payday,
        "paycheck_allocation": paycheck_allocation,
        "debt_target": debt_target.name if debt_target else None,
        "extra_to_debt": extra_to_debt,
        "extra_to_savings": extra_to_savings,
        "extra_to_keep_as_cash": extra_to_keep_as_cash,
        "recommendations": recommendations,
    }
