import logging
import os
from openai import OpenAI
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForensicDebateEngine:
    """
    AAE V3 Layers 9 & 10: Institutional Stress Test.
    Provides contrasting Bear and Bull perspectives for final human decision-making.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        import httpx
        http_client = httpx.Client()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=http_client)

    def run_bear_layer(self, context_data):
        """Layer 9: The Short-Seller / Forensic Bear perspective."""
        logger.info(f"Starting Layer 9 (Bear) for {self.symbol}...")
        prompt = f"""
        You are a Short-Seller / Forensic Bear Analyst. 
        Context: {context_data}
        Task: Argue why {self.symbol} is a 'Value Trap' or a cyclical peak.
        Constraint: Provide exactly 5 concise bullet points. No introductory or concluding text.
        Focus: Margin risks, valuation extremes, sector fatigue, or hidden traps.
        """
        return self.get_llm_response(prompt)

    def run_bull_layer(self, context_data):
        """Layer 10: The Institutional Bull perspective."""
        logger.info(f"Starting Layer 10 (Bull) for {self.symbol}...")
        prompt = f"""
        You are an Institutional Bull Analyst.
        Context: {context_data}
        Task: Argue why {self.symbol} is a high-conviction rerating candidate.
        Constraint: Provide exactly 5 concise bullet points. No introductory or concluding text.
        Focus: Structural inflections, narrative momentum, or market confirmation leadership.
        """
        return self.get_llm_response(prompt)

    def get_llm_response(self, prompt, json_mode=False):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a professional institutional investment analyst."},
                      {"role": "user", "content": prompt}],
            response_format={ "type": "json_object" } if json_mode else None
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    # Test with dummy data
    pass
