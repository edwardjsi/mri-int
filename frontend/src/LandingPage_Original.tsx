import { useState } from 'react';

const heroStats = [
  { label: 'Nifty-beating CAGR', value: '25.4%', detail: 'vs. 11.8% Nifty 50 (17y)' },
  { label: 'Signals per week', value: '23', detail: 'Delivered at 4:30PM IST weekdays' },
  { label: 'Accuracy checkpoint', value: '3+ regimes', detail: 'Validated 2008 / 2020 / sideways' },
];

const featureHighlights = [
  {
    title: 'Regime awareness',
    description: 'Blends SMA-200 regime with 0-100 stock scores to skip Risk-Off stretches.',
  },
  {
    title: 'Digital Twin portfolio',
    description: 'Persist your holdings, grade them instantly, and compare risk vs. MRI live signals.',
  },
  {
    title: 'Automated daily digests',
    description: 'SES-powered emails keep you updated without opening the dashboard.',
  },
];

const testimonials = [
  {
    quote: 'MRI delivered an overnight signal I finally trusted. 14-day free trial made it easy to onboard.',
    name: 'Ananya, Retail investor • Bangalore',
  },
  {
    quote: 'Landing page told the story: regime filter + 0-100 score + persistence. Trial let me backtest real portfolios.',
    name: 'Siddharth, Quant analyst • Mumbai',
  },
];

export function LandingPage_Original({ onRequestAuth }: { onRequestAuth: () => void }) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [status, setStatus] = useState<'idle' | 'success'>('idle');
  const [error, setError] = useState('');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !phone.trim()) {
      setError('Email and phone are required to reserve the trial.');
      setStatus('idle');
      return;
    }
    setError('');
    setStatus('success');
    onRequestAuth();
  };

  return (
    <div className="landing-shell">
      <div className="landing-header">
        <div className="landing-hero-copy">
          <p className="landing-tagline">Market Regime Intelligence</p>
          <h1>Daily quant signals + portfolio risk visibility for Indian investors.</h1>
          <p className="landing-subtitle">MRI blends regime filtering, 0-100 trend scores, and persistent holdings to keep you aligned with risk-on opportunities.</p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => onRequestAuth()}>Enter the dashboard</button>
            <button className="btn-ghost" onClick={() => onRequestAuth()}>Start risk audit</button>
          </div>
          <div className="hero-meta">
            {heroStats.map(stat => (
              <div key={stat.label} className="hero-stat">
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
                <small>{stat.detail}</small>
              </div>
            ))}
          </div>
        </div>
        <div className="landing-hero-card">
          <p className="hero-card-title">Reserve your 14-day free trial</p>
          <form className="landing-trial-form" onSubmit={handleSubmit}>
            <label>
              Work email
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@fundelabs.com"
                required
              />
            </label>
            <label>
              Phone / WhatsApp
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                required
              />
            </label>
            <button type="submit" className="btn-primary">Reserve free trial</button>
          </form>
          {status === 'success' && (
            <p className="landing-form-status">We locked in the trial. Check your inbox — the login panel is ready.</p>
          )}
          {error && (
            <p className="landing-form-error">{error}</p>
          )}
        </div>
      </div>
      <section className="landing-features">
        {featureHighlights.map(feature => (
          <div key={feature.title} className="feature-card">
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
          </div>
        ))}
      </section>
      <section className="landing-testimonials">
        {testimonials.map(item => (
          <div key={item.name} className="testimonial-card">
            <p className="testimonial-quote">“{item.quote}”</p>
            <p className="testimonial-name">{item.name}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
