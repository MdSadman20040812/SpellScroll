'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { catalog } from '../lib/catalog';
import { EmptyState } from '../components/SeriesCard';
import {
  EMPTY_PREFS,
  loadPreferences,
  loadReactions,
  type Preferences,
  type Reaction,
} from '../lib/prefs';

export default function ProfilePage() {
  const [prefs, setPrefs] = useState<Preferences>(EMPTY_PREFS);
  const [reactions, setReactions] = useState<Record<string, Reaction>>({});
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setPrefs(loadPreferences());
    setReactions(loadReactions());
    setReady(true);
  }, []);

  const byId = useMemo(() => new Map(catalog.map((item) => [item.id, item])), []);
  const entries = Object.entries(reactions);

  const reading = entries.filter(([, r]) => r.status === 'reading');
  const completed = entries.filter(([, r]) => r.status === 'completed');
  const skipped = entries.filter(([, r]) => r.status === 'skipped');
  const rated = entries.filter(([, r]) => typeof r.rating === 'number');
  const averageRating = rated.length
    ? (rated.reduce((sum, [, r]) => sum + (r.rating ?? 0), 0) / rated.length).toFixed(1)
    : null;

  const meters = useMemo(() => {
    const affinity = new Map<string, number>();
    for (const [id, reaction] of entries) {
      const item = byId.get(id);
      if (!item) continue;
      const weight = reaction.status === 'skipped' ? -1 : 2;
      for (const genre of item.genres) {
        affinity.set(genre, (affinity.get(genre) ?? 0) + weight);
      }
    }
    const positive = [...affinity.entries()]
      .filter(([, score]) => score > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
    const peak = Math.max(1, ...positive.map(([, score]) => score));
    return positive.map(([name, score]) => ({
      name,
      score,
      percent: Math.round((score / peak) * 100),
    }));
  }, [entries, byId]);

  // Rendering the stored state before hydration finishes would flash empty
  // values, since localStorage is unavailable during SSR.
  if (!ready) {
    return <div className="container" style={{ paddingBlock: 'var(--space-16)' }} />;
  }

  return (
    <div className="container">
      <header className="stack" style={{ paddingBlock: 'var(--space-10) var(--space-8)' }}>
        <p className="eyebrow eyebrow--accent">Your essence</p>
        <h1 className="title-1">Taste signature</h1>
        <p className="lede">Everything the ranker knows about you, and what it learned from.</p>
      </header>

      <div className="stat-grid" style={{ marginBottom: 'var(--space-10)' }}>
        <div className="stat">
          <p className="stat__value accent-text">{reading.length}</p>
          <p className="stat__label">Currently reading</p>
        </div>
        <div className="stat">
          <p className="stat__value" style={{ color: 'var(--accent-2)' }}>{completed.length}</p>
          <p className="stat__label">Finished</p>
        </div>
        <div className="stat">
          <p className="stat__value muted">{skipped.length}</p>
          <p className="stat__label">Skipped</p>
        </div>
        <div className="stat">
          <p className="stat__value" style={{ color: 'var(--ink-amber-400)' }}>
            {averageRating ?? '—'}
          </p>
          <p className="stat__label">Average rating</p>
        </div>
      </div>

      <div
        style={{ display: 'grid', gap: 'var(--space-10)', alignItems: 'start' }}
        className="profile-grid"
      >
        <div className="stack-lg">
          <section className="stack">
            <h2 className="title-3">Genre affinity</h2>
            {meters.length ? (
              <div className="panel stack">
                {meters.map((meter) => (
                  <div className="meter" key={meter.name}>
                    <div className="meter__head">
                      <span className="meter__name">{meter.name}</span>
                      <span className="meter__value">{meter.score}</span>
                    </div>
                    <div
                      className="meter__track"
                      role="img"
                      aria-label={`${meter.name}: affinity ${meter.score}`}
                    >
                      <div className="meter__fill" style={{ width: `${meter.percent}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon="sparkles"
                title="Nothing tracked yet"
                text="React to a few cards in your feed and your genre affinities will build up here."
                action={
                  <Link className="btn btn--primary" href="/feed">
                    Go to your feed
                  </Link>
                }
              />
            )}
          </section>

          {reading.length > 0 && (
            <section className="stack">
              <h2 className="title-3">Reading now</h2>
              <div className="mini-grid">
                {reading.map(([id]) => {
                  const item = byId.get(id);
                  if (!item) return null;
                  return (
                    <Link className="mini" key={id} href={`/series/${item.slug}`} title={item.title}>
                      <img
                        src={item.cover_url}
                        alt={item.title}
                        loading="lazy"
                        width={200}
                        height={300}
                        referrerPolicy="no-referrer"
                      />
                    </Link>
                  );
                })}
              </div>
            </section>
          )}
        </div>

        <aside className="stack">
          <div className="panel stack-sm">
            <h2 className="title-4">In your words</h2>
            {prefs.raw_input ? (
              <p
                className="body-sm"
                style={{
                  padding: 'var(--space-4)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-xs)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {prefs.raw_input}
              </p>
            ) : (
              <p className="body-sm muted">No signature stored yet.</p>
            )}

            {prefs.cleaned_genres.length > 0 && (
              <>
                <p className="body-sm" style={{ marginTop: 'var(--space-3)' }}>Liked genres</p>
                <div className="row row--wrap" style={{ gap: 'var(--space-1)' }}>
                  {prefs.cleaned_genres.map((genre) => (
                    <span className="tag" key={genre}>{genre}</span>
                  ))}
                </div>
              </>
            )}

            {prefs.disliked_themes.length > 0 && (
              <>
                <p className="body-sm" style={{ marginTop: 'var(--space-3)' }}>Avoiding</p>
                <div className="row row--wrap" style={{ gap: 'var(--space-1)' }}>
                  {prefs.disliked_themes.map((theme) => (
                    <span
                      className="tag"
                      key={theme}
                      style={{
                        background: 'rgba(251,113,133,.12)',
                        borderColor: 'rgba(251,113,133,.3)',
                        color: 'var(--ink-rose-400)',
                      }}
                    >
                      {theme}
                    </span>
                  ))}
                </div>
              </>
            )}

            <Link
              className="btn btn--soft btn--block"
              href="/onboarding"
              style={{ marginTop: 'var(--space-4)' }}
            >
              Rewrite my signature
            </Link>
          </div>

          <div className="panel stack-sm">
            <h2 className="title-4">Coverage</h2>
            <p className="body-sm muted">
              You have reacted to <strong>{entries.length}</strong> of{' '}
              <strong>{catalog.length}</strong> series in the archive.
            </p>
            <div className="meter__track" style={{ marginTop: 'var(--space-2)' }}>
              <div
                className="meter__fill"
                style={{ width: `${Math.round((entries.length / catalog.length) * 100)}%` }}
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
