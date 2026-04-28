import os
import json
from openai import OpenAI

# Initialize client only if API key exists to avoid crash on import
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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
    if not client:
        print("WARNING: OpenAI client not initialized. Skipping signal extraction.")
        return []
        
    signals = []

    for d in docs:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": d["text"][:12000]}
                ],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            content = resp.choices[0].message.content
            parsed = json.loads(content)

            for s in parsed.get("signals", []):
                s["source"] = d["source_type"]
                s["date"] = d["date"]
                signals.append(s)
        except Exception as e:
            print(f"Error extracting signals for {d.get('ticker')}: {e}")
            continue

    return signals
