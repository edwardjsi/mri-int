import logging
import os
from openai import OpenAI
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForensicDebateEngine:
    """
    AAE V3 Layer 8: Forensic Debate.
    Synthesizes a Bull vs. Bear debate to stress-test the rerating hypothesis.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run_debate(self, context_data):
        """
        Runs a multi-agent debate and returns a synthesized conviction score.
        context_data: The output from AAEOrchestrator.
        """
        logger.info(f"Starting Forensic Debate for {self.symbol}...")
        
        # 1. The Bull Case
        bull_prompt = f"""
        You are an Institutional Bull Analyst. Argue why {self.symbol} is a high-conviction rerating candidate.
        Context: {context_data}
        Focus on: Structural inflections, narrative momentum, and market confirmation.
        Be aggressive and evidence-based.
        """
        bull_case = self.get_llm_response(bull_prompt)
        
        # 2. The Bear Case
        bear_prompt = f"""
        You are a Short-Seller / Forensic Bear Analyst. Argue why {self.symbol} is a 'Value Trap' or a cyclical peak.
        Context: {context_data}
        Focus on: Margin risks, valuation extremes, sector fatigue, and historical false positives.
        Try to find the 'hidden trap' in the Bull thesis.
        """
        bear_case = self.get_llm_response(bear_prompt)
        
        # 3. The Judicial Synthesis
        judge_prompt = f"""
        You are the Chief Investment Officer (CIO). Synthesize the following debate for {self.symbol}.
        
        BULL CASE:
        {bull_case}
        
        BEAR CASE:
        {bear_case}
        
        VERDICT:
        1. Conviction Score (0-100)
        2. Final Verdict (REJECT / NEUTRAL / HIGH CONVICTION)
        3. Critical Risk Factor to watch.
        
        Return in JSON format: {{"conviction_score": int, "verdict": str, "critical_risk": str, "summary": str}}
        """
        verdict_raw = self.get_llm_response(judge_prompt, json_mode=True)
        
        import json
        try:
            verdict = json.loads(verdict_raw)
        except:
            logger.error(f"Failed to parse Judge verdict for {self.symbol}")
            verdict = {"conviction_score": 50, "verdict": "ERROR", "critical_risk": "N/A", "summary": verdict_raw}
            
        logger.info(f"Forensic Debate Complete for {self.symbol}. Conviction: {verdict['conviction_score']}")
        return {
            "bull_case": bull_case,
            "bear_case": bear_case,
            "verdict": verdict
        }

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
