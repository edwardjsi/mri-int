import pandas as pd
import os
if os.path.exists('scratch/minervini_base.pkl'):
    df = pd.read_pickle('scratch/minervini_base.pkl')
    print("Columns:", list(df.columns))
    if 'stage2' in df.columns:
        print("stage2 present. Total True:", df['stage2'].sum())
    else:
        print("stage2 NOT present.")
else:
    print("minervini_base.pkl not found.")
