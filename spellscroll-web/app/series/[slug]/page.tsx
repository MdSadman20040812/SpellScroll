import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { catalog, getSeries } from '../../lib/catalog';
import { SeriesCard } from '../../components/SeriesCard';
import { Icon } from '../../components/Icons';

type Props = { params: { slug: string } };

export function generateStaticParams() {
  return catalog.map((item) => ({ slug: item.slug }));
}

export function generateMetadata({ params }: Props): Metadata {
  const series = getSeries(params.slug);
  if (!series) return { title: 'Not found — SpellScroll' };
  return {
    title: `${series.title} — SpellScroll`,
    description: series.synopsis.slice(0, 160),
  };
}

const STATUS_LABELS: Record<string, string> = {
  releasing: 'Releasing',
  finished: 'Finished',
  hiatus: 'On hiatus',
  cancelled: 'Cancelled',
  not_yet_released: 'Upcoming',
};

const ORIGIN_LABELS: Record<string, string> = {
  KR: 'Manhwa',
  CN: 'Manhua',
  JP: 'Manga',
};

export default function SeriesPage({ params }: Props) {
  const series = getSeries(params.slug);
  if (!series) notFound();

  const wanted = new Set(series.genres);
  const related = catalog
    .filter((item) => item.id !== series.id)
    .map((item) => ({
      item,
      overlap: item.genres.filter((genre) => wanted.has(genre)).length,
    }))
    .filter((row) => row.overlap > 0)
    .sort((a, b) => b.overlap - a.overlap || (b.item.average_score ?? 0) - (a.item.average_score ?? 0))
    .slice(0, 6)
    .map((row) => row.item);

  return (
    <article style={{ ['--card-accent' as string]: series.accent_color }}>
      <header className="hero">
        {series.banner_url ? (
          <div className="hero__banner">
            <img src={series.banner_url} alt="" referrerPolicy="no-referrer" />
          </div>
        ) : null}

        <div className="container hero__inner">
          <div className="hero__cover">
            <img
              src={series.cover_url}
              alt={`Cover of ${series.title}`}
              width={400}
              height={600}
              referrerPolicy="no-referrer"
            />
          </div>

          <div className="stack">
            <div className="stack-sm">
              {ORIGIN_LABELS[series.country] ? (
                <p className="eyebrow eyebrow--accent">{ORIGIN_LABELS[series.country]}</p>
              ) : null}
              <h1 className="title-1">{series.title}</h1>
            </div>

            <div className="row row--wrap">
              {series.average_score ? (
                <span className="badge badge--score">
                  <Icon name="star" size={12} /> {series.average_score}%
                </span>
              ) : null}
              {series.genres.slice(0, 5).map((genre) => (
                <Link className="tag" href={`/archive`} key={genre}>
                  {genre}
                </Link>
              ))}
            </div>

            <p className="lede">{series.synopsis || 'No synopsis has been published yet.'}</p>

            {series.source_url ? (
              <div className="row row--wrap">
                <a
                  className="btn btn--primary"
                  href={series.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Icon name="external" size={16} /> Read the official release
                </a>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="container stack-lg">
        <section className="meta-list">
          {series.release_year ? (
            <div>
              <p className="meta-list__label">Started</p>
              <p className="meta-list__value">{series.release_year}</p>
            </div>
          ) : null}
          {series.publication_status ? (
            <div>
              <p className="meta-list__label">Status</p>
              <p className="meta-list__value">
                {STATUS_LABELS[series.publication_status] ?? series.publication_status}
              </p>
            </div>
          ) : null}
          {series.chapter_count ? (
            <div>
              <p className="meta-list__label">Chapters</p>
              <p className="meta-list__value">{series.chapter_count}</p>
            </div>
          ) : null}
          <div>
            <p className="meta-list__label">Colour</p>
            <p className="meta-list__value">{series.colour_rating.toFixed(2)}</p>
          </div>
          {series.authors.length ? (
            <div>
              <p className="meta-list__label">Created by</p>
              <p className="meta-list__value">{series.authors.join(', ')}</p>
            </div>
          ) : null}
        </section>

        {series.tags.length ? (
          <section className="stack-sm">
            <h2 className="title-4">Themes</h2>
            <div className="row row--wrap" style={{ gap: 'var(--space-1)' }}>
              {series.tags.map((tag) => (
                <span className="tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        {related.length ? (
          <section className="stack">
            <h2 className="title-3">If you like this</h2>
            <div className="card-grid">
              {related.map((item) => (
                <SeriesCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </article>
  );
}
