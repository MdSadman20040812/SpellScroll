'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Recommendation } from '../lib/catalog';
import { CardSkeleton, EmptyState, SeriesCard } from '../components/SeriesCard';
import { Icon } from '../components/Icons';
import {
  loadPreferences,
  loadReactions,
  saveReaction,
  type Reaction,
} from '../lib/prefs';

export default function FeedPage() {
  const [items, setItems] = useState<Recommendation[]>([]);
  const [reactions, setReactions] = useState<Record<string, Reaction>>({});
  const [genre, setGenre] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [rating, setRating] = useState<{ item: Recommendation; stars: number; note: string } | null>(
    null
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    const prefs = loadPreferences();
    if (!prefs.raw_input) {
      setNeedsOnboarding(true);
      setLoading(false);
      return;
    }
    const current = loadReactions();
    setReactions(current);

    try {
      const response = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: prefs,
          interactedIds: Object.entries(current)
            .filter(([, value]) => value.status === 'skipped')
            .map(([id]) => id),
        }),
      });
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      const data = await response.json();
      setItems(data.webtoons || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the recommender.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const genres = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      for (const value of item.genres || []) {
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const visible = genre ? items.filter((item) => item.genres?.includes(genre)) : items;

  function react(item: Recommendation, status: Reaction['status'], stars?: number, note?: string) {
    const next = saveReaction(item.id, {
      status,
      rating: stars,
      note,
      at: new Date().toISOString(),
    });
    setReactions(next);
    if (status === 'skipped') {
      setItems((current) => current.filter((candidate) => candidate.id !== item.id));
    }
  }

  if (needsOnboarding) {
    return (
      <div className="container" style={{ paddingBlock: 'var(--space-16)' }}>
        <EmptyState
          icon="sparkles"
          title="Tell us what you like first"
          text="SpellScroll needs a taste signature before it can rank anything for you. It takes about a minute."
          action={
            <Link className="btn btn--primary" href="/onboarding">
              Attune your taste
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="container">
      <header
        className="row row--between row--wrap"
        style={{ alignItems: 'flex-end', paddingBlock: 'var(--space-8) var(--space-6)' }}
      >
        <div className="stack-sm">
          <p className="eyebrow eyebrow--accent">Curated for you</p>
          <h1 className="title-1">Your Arcana</h1>
          <p className="body-sm muted">
            Each card explains why it surfaced. React to it and the next cycle shifts.
          </p>
        </div>
        <button className="btn btn--soft" type="button" onClick={load} disabled={loading}>
          <Icon name="refresh" size={16} /> Rebuild feed
        </button>
      </header>

      {items.length > 0 && (
        <div className="scroller" role="group" aria-label="Filter by genre"
             style={{ marginBottom: 'var(--space-6)' }}>
          <button
            className={`chip${genre ? '' : ' is-active'}`}
            type="button"
            aria-pressed={!genre}
            onClick={() => setGenre('')}
          >
            All <span className="chip__count">{items.length}</span>
          </button>
          {genres.map(([name, count]) => (
            <button
              key={name}
              className={`chip${genre === name ? ' is-active' : ''}`}
              type="button"
              aria-pressed={genre === name}
              onClick={() => setGenre(name)}
              style={{ textTransform: 'capitalize' }}
            >
              {name} <span className="chip__count">{count}</span>
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="card-grid">
          {Array.from({ length: 10 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon="alert"
          title="Your feed did not load"
          text={error}
          action={
            <button className="btn btn--primary" type="button" onClick={load}>
              <Icon name="refresh" size={16} /> Try again
            </button>
          }
        />
      ) : visible.length ? (
        <div className="card-grid">
          {visible.map((item, index) => (
            <SeriesCard
              key={item.id}
              item={item}
              rank={index + 1}
              reason={item.reason}
              status={reactions[item.id]?.status}
              actions={
                <>
                  <button
                    className="btn btn--icon btn--danger"
                    type="button"
                    aria-label={`Not for me: ${item.title}`}
                    onClick={() => react(item, 'skipped')}
                  >
                    <Icon name="ghost" size={15} />
                  </button>
                  <button className="btn" type="button" onClick={() => react(item, 'reading')}>
                    <Icon name="book" size={14} /> Reading
                  </button>
                  <button
                    className="btn btn--soft"
                    type="button"
                    onClick={() => setRating({ item, stars: 5, note: '' })}
                  >
                    <Icon name="check" size={14} /> Done
                  </button>
                </>
              }
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Nothing matches that filter"
          text="Try a different genre, or rebuild the feed to pull in new series."
          action={
            <button className="btn btn--primary" type="button" onClick={() => setGenre('')}>
              Show everything
            </button>
          }
        />
      )}

      {rating ? (
        <div className="dialog-backdrop" onClick={(event) => {
          if (event.target === event.currentTarget) setRating(null);
        }}>
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="rate-title">
            <div className="row row--between" style={{ marginBottom: 'var(--space-5)' }}>
              <div>
                <h2 className="title-3" id="rate-title">How was it?</h2>
                <p className="body-sm muted">{rating.item.title}</p>
              </div>
              <button
                className="btn btn--ghost btn--icon"
                type="button"
                aria-label="Close"
                onClick={() => setRating(null)}
              >
                <Icon name="x" />
              </button>
            </div>

            <div className="stack">
              <div className="field">
                <span className="field__label" id="rating-label">Rating</span>
                <div className="stars" role="radiogroup" aria-labelledby="rating-label">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={value === rating.stars}
                      aria-label={`${value} of 5`}
                      className={`stars__btn${value <= rating.stars ? ' is-on' : ''}`}
                      onClick={() => setRating({ ...rating, stars: value })}
                    >
                      <Icon name="star" size={26} />
                    </button>
                  ))}
                </div>
              </div>

              <div className="field">
                <label className="field__label" htmlFor="note">
                  Notes <span className="faint">(optional)</span>
                </label>
                <textarea
                  className="textarea"
                  id="note"
                  rows={3}
                  value={rating.note}
                  onChange={(event) => setRating({ ...rating, note: event.target.value })}
                  placeholder="What worked, what didn't."
                />
              </div>

              <div className="row">
                <button className="btn grow" type="button" onClick={() => setRating(null)}>
                  Cancel
                </button>
                <button
                  className="btn btn--accent2 grow"
                  type="button"
                  onClick={() => {
                    react(rating.item, 'completed', rating.stars, rating.note);
                    setRating(null);
                  }}
                >
                  Save response
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
