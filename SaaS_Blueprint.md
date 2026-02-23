# Market Regime Intelligence (MRI) — SaaS Phase 1 Technical Blueprint

Based on the quant engine logic defined in the Phase 0 viability prototype, the following technical blueprint outlines the architecture for the Phase 1 SaaS product.

---

## 1. Information Architecture (Sitemap)

The application is logically divided into public marketing pages, authentication flows, and the core authenticated application.

- **Public Site**
  - `/` - Landing Page (Value proposition, basic regime status indicator)
  - `/pricing` - Subscription tiers (Retail & Advisor)
  - `/about` - Methodology and disclaimers
- **Authentication**
  - `/auth/login` - Sign in
  - `/auth/register` - Sign up
  - `/auth/forgot-password` - Password recovery
- **Authenticated App (SaaS)**
  - `/app/dashboard` - Main overview (Current Market Regime, Daily Market Health)
  - `/app/screener` - Stock Trend Screener (Filter Nifty 500 by 0-5 scores, EMA metrics)
  - `/app/screener/[symbol]` - Detailed stock view (Scores, historical indicators, volume)
  - `/app/portfolio` - Portfolio Risk Engine (Manage holdings, upload portfolios)
  - `/app/portfolio/risk-analysis` - Current portfolio regime alignment & risk level
  - `/app/settings` - User settings, billing, API keys (if applicable)

---

## 2. User Journey Mapping

Three critical conversion and retention paths for the SaaS user.

### Journey 1: Visitor to Paid Subscriber (Conversion Path)
1. **Entry**: User lands on `/` via organic search or ad. Sees a simplified "Current Regime" widget.
2. **Interest**: Navigates to `/pricing` and clicks "Start 7-Day Free Trial" on the Retail tier.
3. **Action**: Redirected to `/auth/register`. Enters email/password or uses Google OAuth.
4. **Checkout**: Redirected to Stripe Checkout to enter payment details for the trial.
5. **Completion**: Lands on `/app/dashboard`. Onboarding flow explains how to use the Regime and Screener.

### Journey 2: Daily Screener Routine (Core Value Path)
1. **Entry**: User receives daily post-market email alert -> Clicks "View Today's Scores".
2. **Context**: Lands on `/app/dashboard`, sees that Regime is "Risk-On" (Score: 82).
3. **Action**: Navigates to `/app/screener`. Applies filter: `Score >= 4`.
4. **Analysis**: Evaluates the top 10 scoring stocks, checking the "Relative Strength" and "Volume" columns.
5. **Completion**: User exports the list to CSV or adds the top 3 stocks to their personal watch list.

### Journey 3: Portfolio Risk Audit (Engagement Path)
1. **Entry**: User logs in and navigates to `/app/portfolio`.
2. **Action**: User uploads a CSV of their current holdings (or connects via broker API/manual entry).
3. **Analysis**: System calculates individual scores for all holdings and aggregates them.
4. **Insight**: User is presented with `/app/portfolio/risk-analysis` showing a "High Risk" warning because 40% of their portfolio consists of stocks below their 200 EMA during a Neutral market regime.
5. **Completion**: User decides to liquidate low-scoring stocks based on the platform's deterministic rules.

---

## 3. Data Architecture (Schema Models)

To support the dynamic SaaS content while maintaining the core quant engine data, the PostgreSQL RDS schema will expand to include tenant and application state data.

### Multi-Tenant Core Schema
```sql
-- Users and Billing
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    plan_tier VARCHAR(50) DEFAULT 'free', -- 'free', 'retail', 'advisor'
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Portfolios
CREATE TABLE portfolios (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portfolio_items (
    id UUID PRIMARY KEY,
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight DECIMAL(5,2), -- Percentage weight
    quantity DECIMAL(15,4)
);
```

### Quant Engine Read-Replicas (Computed Data)
```sql
-- Market Regime History
CREATE TABLE market_regime (
    date DATE PRIMARY KEY,
    sma_200 DECIMAL(10,2),
    regime_score INT, -- 0 to 100
    classification VARCHAR(20) -- 'Risk-On', 'Risk-Off', etc.
);

-- Daily Stock Scores
CREATE TABLE stock_scores (
    date DATE,
    symbol VARCHAR(50),
    total_score INT, -- 0 to 5
    condition_ema_50_200 BOOLEAN,
    condition_sma_200_slope BOOLEAN,
    condition_6m_high BOOLEAN,
    condition_volume BOOLEAN,
    condition_rs BOOLEAN,
    PRIMARY KEY (date, symbol)
);
```
*(Note: `daily_prices` and calculated indicators remain as built in Phase 0).*

---

## 4. API Surface Definition

The FastAPI backend will expose the following RESTful endpoints to the frontend (Next.js/React).

### Authentication & Users
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Authenticate, return JWT access/refresh tokens
- `GET /api/v1/users/me` - Get current user profile and plan tier
- `POST /api/v1/users/billing/portal` - Generate Stripe Customer Portal session

### Market Regime Data (Read-Only)
- `GET /api/v1/regime/current` - Returns today's regime score and classification.
- `GET /api/v1/regime/history` - Returns time-series data of the regime score vs Nifty 50 for charting.

### Stock Screener (Read-Only)
- `GET /api/v1/screener` - List stocks with query params: `?min_score=4&regime=Risk-On&date=YYYY-MM-DD`. Returns pagination.
- `GET /api/v1/screener/{symbol}` - Detailed historical indicator metrics and score breakdown for a specific stock.

### Portfolio Management (CRUD)
- `GET /api/v1/portfolios` - List user's portfolios.
- `POST /api/v1/portfolios` - Create a new portfolio.
- `PUT /api/v1/portfolios/{id}/items` - Batch update portfolio holdings (manual or CSV upload).
- `GET /api/v1/portfolios/{id}/risk-analysis` - The core engine endpoint: Evaluates the uploaded items against the latest `stock_scores` and `market_regime` to return an aggregated portfolio Risk Level (Low, Moderate, High, Extreme).
