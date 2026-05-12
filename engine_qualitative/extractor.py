import os
import json

def get_openai_client():
    try:
        from openai import OpenAI
        import httpx
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        # Use a custom http_client to avoid the 'proxies' vs 'proxy' argument conflict
        http_client = httpx.Client()
        return OpenAI(api_key=api_key, http_client=http_client)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return None

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
    client = get_openai_client()
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
