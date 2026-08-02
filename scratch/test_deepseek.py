import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_mosi.mosi_compiler import MosiCompiler

# os.environ.pop("OPENAI_API_KEY", None) # Let's see if DeepSeek works

compiler = MosiCompiler()
with open("/home/immanuels/Documents/immanuels/Research/Arvind Fashions.md", "r") as f:
    text = f.read()

try:
    print("Extracting...")
    res = compiler._extract_knowledge_via_llm(text)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
