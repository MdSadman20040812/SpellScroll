'use client';

import Link from 'next/link';
import { useState } from 'react';
import type { Series } from '../lib/catalog';
import { hueFor } from '../lib/catalog';
import { Icon } from './Icons';

type Props = {
  item: Series;
  rank?: number;
  reason?: string;
  status?: string;
  actions?: React.ReactNode;
};

function badgeFor(status?: string) {
  if (status === 'reading') return <span className="badge badge--reading">Reading</span>;
  if (status === 'completed') return <span className="badge badge--completed">Finished</span>;
  if (status === 'skipped') return <span className="badge badge--skipped">Skipped</span>;
  return null;
}

/**
 * The photocard. Identical geometry and tokens to the Django template version:
 * a fixed 2:3 cover frame that never reflows, with `--card-accent` driving the
 * hover glow, tag colour and rank chip.
 */
export function SeriesCard({ item, rank, reason, status, actions }: Props) {
  const [failed, setFailed] = useState(false);

  const meta = [
    item.average_score ? `${item.average_score}%` : null,
    item.release_year ? String(item.release_year) : null,
    item.chapter_count ? `${item.chapter_count} ch` : null,
  ].filter(Boolean);

  const hue = hueFor(item.title);

  return (
    <article className="card" style={{ ['--card-accent' as string]: item.accent_color }}>
      {status ? <div className="card__corner card__corner--start">{badgeFor(status)}</div> : null}
      {rank !== undefined ? (
        <div className="card__corner card__corner--end">
          <span className="card__rank">#{rank}</span>
        </div>
      ) : null}

      <Link className="card__frame" href={`/series/${item.slug}`} aria-label={item.title}>
        {item.cover_url && !failed ? (
          <img
            className="card__img"
            src={item.cover_url}
            alt={`Cover of ${item.title}`}
            width={300}
            height={450}
            loading="lazy"
            decoding="async"
            onError={() => setFailed(true)}
          />
        ) : (
          // The static app has no cover proxy, so an unreachable upstream falls
          // back to the same deterministic gradient the server generates.
          <span
            aria-hidden="true"
            style={{
              display: 'grid',
              placeItems: 'center',
              width: '100%',
              height: '100%',
              background: `linear-gradient(150deg, hsl(${hue} 58% 26%), hsl(${(hue + 56) % 360} 46% 9%))`,
              fontFamily: 'var(--font-display)',
              fontSize: '2.5rem',
              color: 'rgba(255,255,255,.85)',
            }}
          >
            {item.title.slice(0, 2).toUpperCase()}
          </span>
        )}
        <span className="card__scrim" />
        <span className="card__tags">
          {item.genres.slice(0, 2).map((genre) => (
            <span className="card__tag" key={genre}>
              {genre}
            </span>
          ))}
        </span>
      </Link>

      <div className="card__body">
        <h3 className="card__title clamp-2">
          <Link href={`/series/${item.slug}`}>{item.title}</Link>
        </h3>
        {meta.length ? <p className="card__meta">{meta.join(' · ')}</p> : null}
        {reason ? <p className="card__reason clamp-3">{reason}</p> : null}
        {actions ? <div className="card__actions">{actions}</div> : null}
      </div>
    </article>
  );
}

export function CardSkeleton() {
  return (
    <article className="card card--skeleton" aria-hidden="true">
      <div className="card__frame" />
      <div className="card__body">
        <div className="skeleton-line" />
        <div className="skeleton-line skeleton-line--short" />
      </div>
    </article>
  );
}

export function EmptyState({
  title,
  text,
  action,
  icon = 'ghost',
}: {
  title: string;
  text: string;
  action?: React.ReactNode;
  icon?: string;
}) {
  return (
    <div className="state">
      <div className="state__icon">
        <Icon name={icon} size={24} />
      </div>
      <h2 className="title-3">{title}</h2>
      <p className="state__text">{text}</p>
      {action}
    </div>
  );
}
