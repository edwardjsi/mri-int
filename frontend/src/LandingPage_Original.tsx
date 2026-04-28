import { useState } from 'react';

const heroStats = [
  { label: 'System view', value: '3 layers', detail: 'Regime + quality + momentum' },
  { label: 'Delivery rhythm', value: 'Daily', detail: 'Workflow built for post-market review' },
  { label: 'Portfolio context', value: 'Live', detail: 'Signals plus holdings visibility' },
];

const featureHighlights = [
  {
    title: 'Regime awareness',
    description: 'Stay selective when the broader tape weakens instead of forcing risk in hostile conditions.',
  },
  {
    title: 'Digital Twin portfolio',
    description: 'Persist your holdings, grade them instantly, and compare risk vs. MRI live signals.',
  },
  {
    title: 'Automated daily digests',
    description: 'The live experience brings signals, score breakdowns, and holdings context into one operating dashboard.',
  },
];

const testimonials = [
  {
    quote: 'The regime filter and score breakdown made it much easier to understand why a setup was worth attention.',
    name: 'Ananya, Retail investor • Bangalore',
  },
  {
    quote: 'I could see portfolio context and timing in one place instead of stitching together multiple tools.',
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
          <h1>Regime-aware momentum for serious Indian investors.</h1>
          <p className="landing-subtitle">Combine market regime, business quality, and price momentum in one daily workflow so you can focus on strong setups and avoid blind exposure.</p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => onRequestAuth()}>View Top Opportunities</button>
            <button className="btn-ghost" onClick={() => onRequestAuth()}>See How It Works</button>
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
          <p className="hero-card-title">Built for daily decision support</p>
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
            <button type="submit" className="btn-primary">Open the platform</button>
          </form>
          {status === 'success' && (
            <p className="landing-form-status">The login panel is ready. Continue into the platform.</p>
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
