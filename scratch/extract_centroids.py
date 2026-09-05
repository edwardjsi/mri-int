import pandas as pd
import numpy as np

# Same data loading from cai_final_validation.py
from cai_final_validation import load_data, train_and_predict

full_df, df_class, d2_signal_set = load_data()

train_periods = ['Early', 'Middle']
features = ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio']

df_train = df_class[df_class['period'].isin(train_periods)].dropna(subset=features)
medians = df_train[features].median()
iqr = df_train[features].quantile(0.75) - df_train[features].quantile(0.25)
iqr = iqr.replace(0, 1)

cent_1 = (df_train[df_train['target'] == 1][features].median() - medians) / iqr
cent_0 = (df_train[df_train['target'] == 0][features].median() - medians) / iqr

print("FROZEN_CLASSIFIER_PARAMS = {")
print(f"    'features': {features},")
print(f"    'medians': {medians.to_dict()},")
print(f"    'iqr': {iqr.to_dict()},")
print(f"    'centroid_1': {cent_1.to_dict()},")
print(f"    'centroid_0': {cent_0.to_dict()}")
print("}")
