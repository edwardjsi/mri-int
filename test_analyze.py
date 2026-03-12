from src.portfolio_review_engine import analyze_portfolio
import json

holdings = [{'symbol': 'RELIANCE', 'quantity': 10, 'avg_cost': 2500}, {'symbol': 'SMLMAH', 'quantity': 10, 'avg_cost': 500}]
result = analyze_portfolio(holdings)
print(json.dumps(result, indent=2))
