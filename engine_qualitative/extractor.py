import os
import json
from engine_core.llm_client import get_llm_client

def get_openai_client():
    """Legacy wrapper — returns OpenAI-compatible client from shared LLM factory."""
    client, _model = get_llm_client()
    return client

PROMPT = """
You are extracting INVESTMENT SIGNALS from company disclosures.

Extract ONLY:
1) pricing_power
2) demand
3) cost_pressure
4) expansion
5) working_capital
6) segment_shift
7) risks

Rules:
- No numbers unless explicitly stated
- No guesses
- Return short bullets
- Tag each: {type, polarity: positive|negative|neutral, confidence: low|medium|high}

Return JSON:
{"signals":[ ... ]}
"""

def extract_signals(docs):
    _client, model = get_llm_client()
    if not _client:
        print("WARNING: LLM client not initialized. Skipping signal extraction.")
        return []

    signals = []

    for d in docs:
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": d["text"][:12000]}
                ],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            cont = resp.choices[0].message.content
            parsed = json.loads(cont)

            for s in parsed.get("signals", []):
                s["source"] = d["source_type"]
                s["date"] = d["date"]
                signals.append(s)
        except Exception as e:
            print(f"Error extracting signals for {d.get('ticker')}: {e}")
            continue

    return signals
