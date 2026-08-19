"""In-app AI insight: one LLM call on already-aggregated numbers (never raw rows)."""

PROMPT = """You are an assistant inside a data app for Kosovar farmers deciding WHEN TO SELL a selected product.
Use only the aggregated data below. Write exactly 3 short sentences in simple English:
1) compare the current national price and its date with the seasonal norm and sample size,
2) describe the Kosovo-wide price-cost proxy or an exploratory weather finding without calling it a cause,
3) give a conditional selling-timing tip and mention uncertainty.
Do not recommend what to plant, do not claim profit, do not claim causation, do not invent missing data, and include the data period. No preamble or markdown.

DATA:
{context}
"""

def generate_insight(context: str, api_key: str | None):
    """Returns the insight text, or None if no key / call fails (app shows a note instead)."""
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": PROMPT.format(context=context)}],
        )
        return "".join(b.text for b in msg.content if b.type == "text").strip()
    except Exception as exc:
        print(f"[ai] insight call failed: {exc}")
        return None


def rule_based_summary(crop, latest, month_row, high_month, ratio_row, matched_months: int) -> str:
    """Honest offline narrative when the optional LLM cannot be used."""
    delta = latest["price"] - month_row["avg"]
    direction = "above" if delta >= 0 else "below"
    return (
        f"Rule-based summary: {crop} had an ASK price value of {latest['price']:.2f} in {latest['date']:%B %Y}, "
        f"{abs(delta):.2f} {direction} its historical {latest['date']:%B} average (n={int(month_row['n'])}). "
        f"The Kosovo-wide price-cost index ratio was {ratio_row['margin']:.1f} in {ratio_row['date']:%B %Y}; this is not a farm profit margin. "
        f"Consider historical timing around {high_month}, but treat it as a baseline with uncertainty; weather comparisons use only {matched_months} matched national-price/regional-weather months."
    )
