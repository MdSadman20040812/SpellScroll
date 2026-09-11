'use client';

import { useMemo, useState } from 'react';
import { catalog, genreFacets, hueFor } from '../lib/catalog';
import { SeriesCard, EmptyState } from '../components/SeriesCard';
import { Icon } from '../components/Icons';

type Sort = 'popular' | 'score' | 'colour' | 'newest' | 'title';

const SORTS: { value: Sort; label: string }[] = [
  { value: 'popular', label: 'Most popular' },
  { value: 'score', label: 'Highest rated' },
  { value: 'colour', label: 'Most colourful' },
  { value: 'newest', label: 'Newest first' },
  { value: 'title', label: 'A–Z' },
];

export default function ArchivePage() {
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('');
  const [sort, setSort] = useState<Sort>('popular');

  const facets = useMemo(() => genreFacets().slice(0, 24), []);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    let items = catalog.filter((item) => {
      const matchesGenre = !genre || item.genres.includes(genre);
      const matchesQuery =
        !needle ||
        item.title.toLowerCase().includes(needle) ||
        item.synopsis.toLowerCase().includes(needle);
      return matchesGenre && matchesQuery;
    });

    items = [...items].sort((a, b) => {
      switch (sort) {
        case 'score':
          return (b.average_score ?? 0) - (a.average_score ?? 0);
        case 'colour':
          return b.colour_rating - a.colour_rating;
        case 'newest':
          return (b.release_year ?? 0) - (a.release_year ?? 0);
        case 'title':
          return a.title.localeCompare(b.title);
        default:
          return a.popularity_rank - b.popularity_rank;
      }
    });
    return items;
  }, [query, genre, sort]);

  return (
    <div className="container">
      <header className="stack" style={{ paddingBlock: 'var(--space-10) var(--space-6)' }}>
        <p className="eyebrow eyebrow--accent">The Archive</p>
        <h1 className="title-1">{catalog.length} colourful series, indexed</h1>
        <p className="lede">
          Everything the recommendation agents can draw from. Search it directly, or narrow by
          genre.
        </p>
      </header>

      <div
        className="row row--wrap"
        style={{ marginBottom: 'var(--space-6)' }}
        role="search"
      >
        <div className="search">
          <Icon name="search" size={17} className="search__icon" />
          <label className="visually-hidden" htmlFor="q">
            Search the archive
          </label>
          <input
            className="input"
            id="q"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search titles and synopses…"
          />
        </div>

        <label className="visually-hidden" htmlFor="sort">
          Sort by
        </label>
        <select
          className="select"
          id="sort"
          style={{ width: 'auto', minWidth: 168 }}
          value={sort}
          onChange={(event) => setSort(event.target.value as Sort)}
        >
          {SORTS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {(query || genre) && (
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() => {
              setQuery('');
              setGenre('');
            }}
          >
            Clear
          </button>
        )}
      </div>

      <div
        className="scroller"
        role="group"
        aria-label="Filter by genre"
        style={{ marginBottom: 'var(--space-8)' }}
      >
        <button
          className={`chip${genre ? '' : ' is-active'}`}
          type="button"
          aria-pressed={!genre}
          onClick={() => setGenre('')}
        >
          All <span className="chip__count">{catalog.length}</span>
        </button>
        {facets.map((facet) => (
          <button
            key={facet.name}
            className={`chip${genre === facet.name ? ' is-active' : ''}`}
            type="button"
            aria-pressed={genre === facet.name}
            onClick={() => setGenre(facet.name)}
            style={{ textTransform: 'capitalize', ['--hue' as string]: hueFor(facet.name) }}
          >
            {facet.name} <span className="chip__count">{facet.count}</span>
          </button>
        ))}
      </div>

      <p className="eyebrow" style={{ marginBottom: 'var(--space-4)' }} aria-live="polite">
        {results.length} result{results.length === 1 ? '' : 's'}
      </p>

      {results.length ? (
        <div className="card-grid">
          {results.map((item) => (
            <SeriesCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon="search"
          title="Nothing found"
          text={`No series matches “${query}”${genre ? ` in ${genre}` : ''}.`}
          action={
            <button
              className="btn btn--primary"
              type="button"
              onClick={() => {
                setQuery('');
                setGenre('');
              }}
            >
              Show everything
            </button>
          }
        />
      )}
    </div>
  );
}
