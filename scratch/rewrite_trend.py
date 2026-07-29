import re

with open("frontend/src/TrendScreen.tsx", "r") as f:
    content = f.read()

# Add imports
content = content.replace(
    "import { api } from './api';", 
    "import { api } from './api';\nimport { CaiCandidateReview } from './CaiCandidateReview';"
)

# Update SortCol type
content = content.replace(
    "type SortCol = 'symbol' | 'close' | 'ema_10' | 'ema_50' | 'ema_200' | 'rolling_high_52w' | 'market_cap_cr' | 'mri_score';",
    "type SortCol = 'symbol' | 'close' | 'ema_10' | 'ema_50' | 'ema_200' | 'rolling_high_52w' | 'market_cap_cr' | 'mri_score' | 'breakout_state' | 'mosi_lite_score';"
)

# Update COL_DEFS
col_defs_old = """const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '\\u20b9' },
  { key: 'ema_10', label: 'EMA10' },
  { key: 'ema_50', label: 'EMA50' },
  { key: 'ema_200', label: 'EMA200' },
  { key: 'rolling_high_52w', label: '52w High' },
  { key: 'market_cap_cr', label: 'Mkt Cap (Cr)' },
  { key: 'mri_score', label: 'MRI' },
];"""

col_defs_new = """const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '₹' },
  { key: 'ema_10', label: 'EMA10' },
  { key: 'ema_50', label: 'EMA50' },
  { key: 'ema_200', label: 'EMA200' },
  { key: 'rolling_high_52w', label: '52w High' },
  { key: 'market_cap_cr', label: 'Mkt Cap (Cr)' },
  { key: 'mri_score', label: 'MRI' },
  { key: 'breakout_state', label: 'State' },
  { key: 'mosi_lite_score', label: 'MOSI' },
];"""
content = content.replace(col_defs_old, col_defs_new)

# Replace sortIndicator unicode
content = content.replace("' \\u25b2' : ' \\u25bc'", "' ▲' : ' ▼'")

# Add state
content = content.replace(
    "const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');",
    "const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');\n  const [reviewSymbol, setReviewSymbol] = useState<string | null>(null);"
)

# Replace unicode in loading and empty state
content = content.replace("Scanning trend screen\\u2026", "Scanning trend screen…")
content = content.replace("\\ud83d\\udcca Trend Screen", "📊 Trend Screen")
content = content.replace("1,000\\u201375,000 Cr", "1,000–75,000 Cr")
content = content.replace("\\ud83c\\udfaf Matches", "🎯 Matches")
content = content.replace("\\u26a0\\ufe0f Market cap data unavailable \\u2014 excluding cap filters", "⚠️ Market cap data unavailable — excluding cap filters")

# Update table headers
content = content.replace("<th>State</th>\n                <th>MOSI</th>", "<th>CAI</th>")

# In the table rows, replace unicode and add Review button
content = content.replace("\\u20b9", "₹")
content = content.replace("\\u2014", "—")

# Update the MOSI td
old_mosi_td = """                    <td>
                      <span style={{ color: mosi >= 70 ? '#22c55e' : mosi >= 50 ? '#f59e0b' : '#94a3b8', fontSize: '13px' }}>
                        {mosi.toFixed(1)}
                      </span>
                    </td>"""

new_mosi_td = """                    <td>
                      <span style={{ color: mosi >= 70 ? '#22c55e' : mosi >= 50 ? '#f59e0b' : '#94a3b8', fontSize: '13px' }}>
                        {mosi.toFixed(1)}
                      </span>
                    </td>
                    <td>
                      <button
                        className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-2 py-1 rounded"
                        onClick={(e) => { e.stopPropagation(); setReviewSymbol(item.symbol); }}
                      >
                        Review
                      </button>
                    </td>"""
content = content.replace(old_mosi_td, new_mosi_td)

# Add the CaiCandidateReview modal at the end of return block
modal_code = """
      {reviewSymbol && (
        <div className="fixed inset-0 bg-black/80 z-[100] flex items-center justify-center p-4" onClick={() => setReviewSymbol(null)}>
          <div className="bg-gray-900 w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-gray-700 shadow-2xl" onClick={e => e.stopPropagation()}>
            <CaiCandidateReview symbol={reviewSymbol} onClose={() => setReviewSymbol(null)} />
          </div>
        </div>
      )}
    </div>
  );
}
"""

content = content.replace("    </div>\n  );\n}", modal_code)

with open("frontend/src/TrendScreen.tsx", "w") as f:
    f.write(content)

