'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Icon } from '../components/Icons';
import { extractPreferences, loadPreferences, savePreferences } from '../lib/prefs';

const SEEDS = [
  { label: 'Slow-burn romance', phrase: 'slow-burn romance with real emotional stakes' },
  { label: 'Dark fantasy', phrase: 'dark fantasy with a heavy atmosphere' },
  { label: 'Power fantasy', phrase: 'power fantasy where the lead grows stronger over time' },
  { label: 'Cultivation', phrase: 'murim and cultivation stories' },
  { label: 'Psychological', phrase: 'psychological thrillers that get under my skin' },
  { label: 'Comedy', phrase: 'comedy with sharp character writing' },
  { label: 'Isekai', phrase: 'isekai and regression premises' },
  { label: 'Slice of life', phrase: 'gentle slice-of-life stories' },
  { label: 'Bold art', phrase: 'bold, high-contrast art that goes wild during action scenes' },
  { label: 'Mystery', phrase: 'mysteries with a real payoff' },
  { label: 'Sports', phrase: 'sports stories about obsession and rivalry' },
  { label: 'Horror', phrase: 'horror that actually unsettles me' },
];

const MIN = 20;
const MAX = 1200;

export default function OnboardingPage() {
  const router = useRouter();
  const [text, setText] = useState('');
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const existing = loadPreferences();
    if (existing.raw_input) {
      setText(existing.raw_input);
    }
  }, []);

  function toggleSeed(phrase: string) {
    const next = new Set(picked);
    if (next.has(phrase)) {
      next.delete(phrase);
      setText((current) =>
        current
          .replace(new RegExp(`(^|[,.]\\s*)${phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'i'), '$1')
          .replace(/\s*,\s*,/g, ',')
          .replace(/^\s*[,.]\s*/, '')
          .trim()
      );
    } else {
      next.add(phrase);
      setText((current) =>
        current.trim() ? `${current.trim().replace(/[.\s]*$/, '')}, ${phrase}` : phrase
      );
    }
    setPicked(next);
  }

  async function submit() {
    setSaving(true);
    // The keyword extractor runs locally and always succeeds, so onboarding
    // never blocks on a network call or an API key.
    savePreferences(extractPreferences(text.trim()));
    router.push('/feed');
  }

  const length = text.trim().length;
  const ready = length >= MIN;

  return (
    <div
      className="container stack-lg"
      style={{ maxWidth: 660, paddingBlock: 'var(--space-12) var(--space-16)' }}
    >
      <div className="stack">
        <div className="row" style={{ gap: 'var(--space-2)' }} aria-hidden="true">
          <span
            style={{
              height: 3,
              flex: 1,
              borderRadius: 'var(--radius-full)',
              background: 'var(--accent)',
            }}
          />
          <span
            style={{
              height: 3,
              flex: 1,
              borderRadius: 'var(--radius-full)',
              background: ready ? 'var(--accent)' : 'var(--surface-raised)',
            }}
          />
        </div>
        <p className="eyebrow eyebrow--accent">Step 1 of 2 &middot; Taste signature</p>
        <h1 className="title-1">What do you actually want to read?</h1>
        <p className="lede">
          Write it the way you would tell a friend. Tone, pacing and art-style cues help more
          than bare genre names.
        </p>
      </div>

      <section className="panel stack">
        <div className="field">
          <label className="field__label" htmlFor="preferences">
            Describe your taste
          </label>
          <textarea
            className="textarea"
            id="preferences"
            rows={6}
            maxLength={MAX}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="e.g. Slow-burn romance with real emotional stakes, and cultivation stories where the art goes wild during fights. I bounce off gag comedy and anything with a tragic ending."
          />
          <div className="row row--between" style={{ marginTop: 'var(--space-2)' }}>
            <p className="field__hint">A sentence or two is plenty.</p>
            <p
              className="field__hint"
              style={{
                fontVariantNumeric: 'tabular-nums',
                color: length > 0 && length < MIN ? 'var(--ink-amber-400)' : undefined,
              }}
              aria-live="polite"
            >
              {text.length}/{MAX}
            </p>
          </div>
        </div>

        <div className="stack-sm">
          <p className="eyebrow">Or start from these</p>
          <div className="seed-grid" role="group" aria-label="Suggested taste seeds">
            {SEEDS.map((seed) => (
              <button
                key={seed.phrase}
                type="button"
                className="seed"
                aria-pressed={picked.has(seed.phrase)}
                onClick={() => toggleSeed(seed.phrase)}
              >
                <span>{seed.label}</span>
                {picked.has(seed.phrase) ? <Icon name="check" size={14} /> : null}
              </button>
            ))}
          </div>
        </div>

        <button
          className="btn btn--primary btn--lg btn--block"
          type="button"
          disabled={!ready || saving}
          onClick={submit}
        >
          {saving ? 'Building your feed…' : 'Forge my signature'}
        </button>
      </section>
    </div>
  );
}
