import pandas as pd

# Load FULL historical SUZLON history first
df = pd.read_csv(
    "backups/20260304/daily_prices.csv",
    low_memory=False
)

df["date"] = pd.to_datetime(df["date"])

df = df[df["symbol"] == "SUZLON"].copy()
df = df.sort_values("date").reset_index(drop=True)

# ------------------------------------------------------------
# WEEKLY DATA
# ------------------------------------------------------------

df = df.set_index("date")

wdf = df.resample("W-FRI").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last"
}).dropna()

# EXACT previous 10 COMPLETED weeks
wdf["w_high_10"] = (
    wdf["high"]
    .rolling(window=10, min_periods=10)
    .max()
    .shift(1)
)

# ------------------------------------------------------------
# PRINT RELEVANT WEEKLY LEVELS
# ------------------------------------------------------------

print("\nWEEKLY THRESHOLDS")
print("=" * 80)

print(
    wdf.loc[
        "2023-04-01":"2023-05-31",
        ["high", "close", "w_high_10"]
    ].to_string()
)

# ------------------------------------------------------------
# DAILY DATA WITH WEEKLY LEVEL MAPPED ONTO EACH DAY
# ------------------------------------------------------------

daily = df.copy()

# Map the most recently completed Friday's weekly threshold
weekly_levels = wdf[["w_high_10"]].copy()

daily = daily.join(
    weekly_levels,
    how="left",
    rsuffix="_weekly"
)

daily["w_high_10"] = daily["w_high_10"].ffill()

# ------------------------------------------------------------
# INSPECT EXACT SUZLON MICRO-RUN WINDOW
# ------------------------------------------------------------

print("\nDAILY SUZLON EVENTS")
print("=" * 80)

window = daily.loc[
    "2023-05-19":"2023-05-30",
    ["open", "high", "low", "close", "w_high_10"]
].copy()

window["above_w_high"] = (
    window["close"] > window["w_high_10"]
)

print(window.to_string())

# ------------------------------------------------------------
# CHECK WHETHER THE SAME WEEKLY THRESHOLD IS REUSED
# ------------------------------------------------------------

print("\nTHRESHOLD TRANSITIONS")
print("=" * 80)

for dt, row in window.iterrows():
    print(
        f"{dt.date()} | "
        f"Close={row['close']:.2f} | "
        f"W10={row['w_high_10']:.2f} | "
        f"Above={row['above_w_high']}"
    )
