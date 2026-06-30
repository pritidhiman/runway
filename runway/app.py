from pathlib import Path
import sys

import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runway.models import Bill, CreditCard
from runway.planner import calculate_plan, get_cushion_target


def main() -> None:
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

    next_paycheck_amount = st.number_input(
        "Next paycheck amount",
        min_value=0.0,
        value=4300.0,
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

    st.divider()

    st.header("Planning settings")

    plan_mode = st.selectbox(
        "Plan mode",
        ["Survival", "Balanced", "Paydown"],
        index=0,
        help=(
            "Survival preserves cash, Balanced splits extra cash, "
            "and Paydown sends extra cash to debt."
        ),
    )

    debt_strategy = st.selectbox(
        "Debt strategy",
        ["Avalanche", "Snowball"],
        index=0,
        help=(
            "Avalanche targets the highest APR card. "
            "Snowball targets the smallest balance."
        ),
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
            credit_limit = st.number_input(
                f"Credit limit {i + 1}",
                min_value=0.0,
                value=0.0,
                help="Leave at $0 if you do not want Runway to check limit risk for this card.",
            )
            expected_new_charges = st.number_input(
                f"Expected new charges before due date {i + 1}",
                min_value=0.0,
                value=0.0,
            )
            due = st.date_input(f"Card due date {i + 1}")
            cards.append(
                CreditCard(
                    name=name,
                    balance=balance,
                    apr=apr,
                    minimum_payment=minimum,
                    due_date=due,
                    credit_limit=credit_limit or None,
                    expected_new_charges_until_due=expected_new_charges,
                )
            )

    st.divider()

    if st.button("Create plan"):
        plan = calculate_plan(
            checking_balance=checking_balance,
            next_paycheck_amount=next_paycheck_amount,
            next_paycheck_date=next_paycheck_date,
            essential_spending_until_payday=essential_spending,
            cushion_target=cushion_target,
            plan_mode=plan_mode,
            debt_strategy=debt_strategy,
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
            st.metric(
                "Risk level",
                plan["risk_level"],
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
            st.metric(
                "Current-cycle extra",
                f"${plan['spendable_extra_before_payday']:,.2f}",
            )

        if plan["risk_level"] == "Red":
            st.error("You are short before payday with the current plan.")
        elif plan["risk_level"] == "Yellow":
            st.warning("You can make it, but cash flow is tight.")
        else:
            st.success("You can make it to payday with your cushion protected.")

        st.subheader("Before payday breakdown")

        st.write(f"Days until paycheck: {plan['days_to_paycheck']}")
        st.write(f"Bills due: ${plan['total_bills_due']:,.2f}")
        st.write(f"Credit card minimums due: ${plan['total_minimums_due']:,.2f}")
        st.write(
            f"Extra card limit protection: "
            f"${plan['card_limit_safety_payments_due']:,.2f}"
        )
        st.write(f"Essential spending: ${plan['essential_spending']:,.2f}")
        st.write(f"Cash cushion: ${plan['cushion_target']:,.2f}")

        if plan["card_limit_risks"]:
            st.subheader("Card limit risk")

            for risk in plan["card_limit_risks"]:
                if risk["risk_level"] == "Over-limit risk":
                    st.error(
                        f"{risk['card_name']}: minimum payment may not be enough. "
                        f"Estimated extra needed above minimum: "
                        f"${risk['additional_payment_needed_above_minimum']:,.2f}."
                    )
                elif risk["risk_level"] == "Near limit":
                    st.warning(
                        f"{risk['card_name']}: projected utilization after minimum "
                        f"is {risk['projected_utilization'] * 100:.1f}%."
                    )
                else:
                    st.success(
                        f"{risk['card_name']}: projected to stay under the limit "
                        f"after the minimum payment."
                    )

                st.write(
                    f"Projected available credit after minimum: "
                    f"${risk['available_credit_after_minimum']:,.2f}"
                )

        st.subheader("Before payday allocation")

        for category, amount in plan["paycheck_allocation"].items():
            st.write(f"{category}: ${amount:,.2f}")

        if plan["spendable_extra_before_payday"] > 0:
            st.success(
                f"Current-cycle extra after required expenses and cushion: "
                f"${plan['spendable_extra_before_payday']:,.2f}"
            )
        else:
            st.error(
                f"Shortfall before payday: "
                f"${abs(plan['cash_left_before_payday']):,.2f}"
            )

        st.subheader("On payday")
        st.write(
            f"Next paycheck reserved for the next cycle: "
            f"${plan['next_paycheck_reserved_for_next_cycle']:,.2f}"
        )
        st.caption(
            "Runway does not treat the next paycheck as extra until next-cycle bills "
            "and essentials are included."
        )

        if plan["debt_target"] and plan["extra_to_debt"] > 0:
            st.info(
                f"Recommended debt target: {plan['debt_target']} "
                f"(${plan['extra_to_debt']:,.2f})"
            )

        st.subheader("Recommendations")

        for rec in plan["recommendations"]:
            st.write(f"- {rec}")


if __name__ == "__main__":
    main()
