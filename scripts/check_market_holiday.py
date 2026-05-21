#!/usr/bin/env python3
"""
Check if today is a NSE/BSE market holiday.
Exits with code 0 (continue) or 1 (skip pipeline).
"""

from datetime import date

# NSE Market Holidays for 2026
NSE_HOLIDAYS_2026 = [
    date(2026, 1, 14),   # Makar Sankranti
    date(2026, 1, 26),   # Republic Day
    date(2026, 2, 19),   # Chhatrapati Shivaji Maharaj Jayanti
    date(2026, 3, 6),    # Mahashivratri
    date(2026, 3, 31),   # Eid-ul-Fitr
    date(2026, 4, 2),    # Ram Navami
    date(2026, 4, 6),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    # date(2026, 5, 21),   # Buddha Pournima – not a market holiday
    date(2026, 8, 15),   # Independence Day
    date(2026, 8, 27),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 21),  # Diwali (Laxmi Pujan)
    date(2026, 11, 4),   # Diwali (Balipratipada)
    date(2026, 11, 20),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
]

today = date.today()

if today in NSE_HOLIDAYS_2026:
    print(f"🎯 Market holiday detected: {today} — skipping pipeline")
    exit(1)
else:
    print(f"✅ Trading day: {today} — proceeding with pipeline")
    exit(0)
