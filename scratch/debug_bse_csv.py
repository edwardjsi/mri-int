import pandas as pd
df = pd.read_csv("BSET1A.csv", index_col=False)
print("Columns:", df.columns.tolist())
print("First row:\n", df.iloc[0].to_dict())
