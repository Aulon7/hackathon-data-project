"""In-app AI insight: one LLM call on already-aggregated numbers (never raw rows)."""

PROMPT = """You are an assistant inside a data app for Kosovar farmers.
Below is this month's aggregated data for the crop the farmer selected.
Write exactly 3 short sentences in simple English a farmer would understand:
1) what the current price is doing vs its seasonal norm,
2) one thing worth knowing from weather or input costs,
3) one clearly-labelled anomaly IF anything is unusual, otherwise a practical tip.
Then repeat the same 3 sentences in Albanian. No preamble, no markdown.

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
