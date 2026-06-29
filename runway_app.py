from datetime import date
from typing import List

import streamlit as st
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


def days_until(target_date: date) -> int:
    return max((target_date - date.today()).days, 1)


def get_cushion_target(
    cushion_mode: str,
    checking_balance: float,
    custom_cushion: float,
) -> float:
    """
    Returns the amount of cash the user wants to preserve as a cushion.

    This prevents the app from treating every dollar as spendable.
    """

    if cushion_mode == "Bare minimum":
        return max(100.0, checking_balance * 0.05)

    if cushion_mode == "Standard":
        return max(250.0, checking_balance * 0.10)

    if cushion_mode == "Conservative":
        return max(500.0, checking_balance * 0.15)

    return custom_cushion


def calculate_plan(
    checking_balance: float,
    next_paycheck_date: date,
    essential_spending_until_payday: float,
    cushion_target: float,
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

    highest_apr_card = max(cards, key=lambda card: card.apr) if cards else None

    recommendations = []

    if runway_after_required < 0:
        recommendations.append(
            "Crisis mode: you do not have enough cash to cover bills, minimum payments, essentials, and your selected cushion before payday."
        )
        recommendations.append(
            "Prioritize housing, utilities, food, transportation, medicine, pets, and credit card minimums. Do not make extra debt payments yet."
        )
    else:
        recommendations.append(
            "You can cover required expenses and preserve your cushion before payday if spending stays within the safe daily amount."
        )

    if highest_apr_card and runway_after_required > 0:
        recommendations.append(
            f"After required expenses and your cushion are protected, put extra cash toward {highest_apr_card.name}, because it has the highest APR at {highest_apr_card.apr:.2f}%."
        )
    elif highest_apr_card:
        recommendations.append(
            f"Do not make extra payments toward {highest_apr_card.name} yet. Preserve cash until required expenses are covered."
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
        "recommendations": recommendations,
    }


st.set_page_config(page_title="Runway", page_icon="💸")

st.title("Runway")
st.subheader("Paycheck and debt planner")

st.write(
    "Runway helps you figure out whether you can make it to your next paycheck, "
    "what must be paid first, and how much cash you should preserve as a cushion."
)

st.divider()

st.header("Cash flow")

checking_balance = st.number_input(
    "Current checking balance",
    min_value=0.0,
    value=842.0,
)

next_paycheck_date = st.date_input(
    "Next paycheck date",
)

essential_spending = st.number_input(
    "Essential spending needed until next paycheck",
    min_value=0.0,
    value=300.0,
    help="Groceries, transportation, medicine, pet food, etc.",
)

st.subheader("Cash cushion")

cushion_mode = st.selectbox(
    "Cash cushion mode",
    ["Bare minimum", "Standard", "Conservative", "Custom"],
    index=1,
    help=(
        "This keeps the app from treating all remaining cash as spendable. "
        "Standard is a good default when cash is tight."
    ),
)

custom_cushion = 0.0

if cushion_mode == "Custom":
    custom_cushion = st.number_input(
        "Custom cushion amount",
        min_value=0.0,
        value=250.0,
    )

cushion_target = get_cushion_target(
    cushion_mode=cushion_mode,
    checking_balance=checking_balance,
    custom_cushion=custom_cushion,
)

st.info(f"Current cushion target: ${cushion_target:,.2f}")

st.divider()

st.header("Bills")

num_bills = st.number_input(
    "Number of bills due before or around payday",
    min_value=0,
    max_value=10,
    value=2,
)

bills = []

for i in range(num_bills):
    with st.expander(f"Bill {i + 1}", expanded=True):
        name = st.text_input(f"Bill name {i + 1}", value=f"Bill {i + 1}")
        amount = st.number_input(
            f"Bill amount {i + 1}",
            min_value=0.0,
            value=100.0,
        )
        due = st.date_input(f"Bill due date {i + 1}")
        bills.append(Bill(name=name, amount=amount, due_date=due))

st.divider()

st.header("Credit cards")

num_cards = st.number_input(
    "Number of credit cards",
    min_value=0,
    max_value=10,
    value=2,
)

cards = []

for i in range(num_cards):
    with st.expander(f"Card {i + 1}", expanded=True):
        name = st.text_input(f"Card name {i + 1}", value=f"Card {i + 1}")
        balance = st.number_input(
            f"Balance {i + 1}",
            min_value=0.0,
            value=1000.0,
        )
        apr = st.number_input(
            f"APR {i + 1}",
            min_value=0.0,
            value=27.99,
        )
        minimum = st.number_input(
            f"Minimum payment {i + 1}",
            min_value=0.0,
            value=75.0,
        )
        due = st.date_input(f"Card due date {i + 1}")
        cards.append(
            CreditCard(
                name=name,
                balance=balance,
                apr=apr,
                minimum_payment=minimum,
                due_date=due,
            )
        )

st.divider()

if st.button("Create plan"):
    plan = calculate_plan(
        checking_balance=checking_balance,
        next_paycheck_date=next_paycheck_date,
        essential_spending_until_payday=essential_spending,
        cushion_target=cushion_target,
        bills=bills,
        cards=cards,
    )

    st.header("Your Runway Plan")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Required before payday",
            f"${plan['required_before_payday']:,.2f}",
        )
        st.metric(
            "Cash cushion reserved",
            f"${plan['cushion_target']:,.2f}",
        )

    with col2:
        st.metric(
            "Runway after required expenses",
            f"${plan['runway_after_required']:,.2f}",
        )
        st.metric(
            "Safe daily spend",
            f"${plan['safe_daily_spend']:,.2f}/day",
        )

    if plan["runway_after_required"] < 0:
        st.error("You are short before payday with the current plan.")
    elif plan["safe_daily_spend"] < 20:
        st.warning("You can make it, but cash flow is tight.")
    else:
        st.success("You can make it to payday with your cushion protected.")

    st.subheader("Breakdown")

    st.write(f"Days until paycheck: {plan['days_to_paycheck']}")
    st.write(f"Bills due: ${plan['total_bills_due']:,.2f}")
    st.write(f"Credit card minimums due: ${plan['total_minimums_due']:,.2f}")
    st.write(f"Essential spending: ${plan['essential_spending']:,.2f}")
    st.write(f"Cash cushion: ${plan['cushion_target']:,.2f}")

    st.subheader("Recommendations")

    for rec in plan["recommendations"]:
        st.write(f"- {rec}")