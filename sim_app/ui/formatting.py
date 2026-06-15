"""Formatting helpers for Streamlit views."""

import pandas as pd


def money(value):
    return round(float(value), 2)


def display_number(value):
    value = money(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def display_euro(value):
    return f"{display_number(value)} €"


def month_sum(values):
    return money(sum(values.values()))


def display_value_table(values, get_category_label, category_header, value_header):
    rows = [(get_category_label(category), display_number(amount)) for category, amount in values.items()]
    return pd.DataFrame(rows, columns=[category_header, value_header])


__all__ = [
    "display_euro",
    "display_number",
    "display_value_table",
    "money",
    "month_sum",
]

