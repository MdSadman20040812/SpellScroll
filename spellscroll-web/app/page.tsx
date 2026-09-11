import Link from 'next/link';
import { catalog, genreFacets } from './lib/catalog';
import { Icon } from './components/Icons';
import { Logo } from './components/Logo';

export default function LandingPage() {
  const showcase = catalog.slice(0, 18);
  const columns = [0, 1, 2].map((offset) =>
    showcase.filter((_, index) => index % 3 === offset)
  );
  const genres = genreFacets();

  return (
    <div className="container">
      <section className="hero-split">
        <div className="stack-lg">
          <div className="stack">
            <p className="eyebrow eyebrow--accent">
              Multi-agent curation &middot; {catalog.length} colourful series
            </p>
            <h1 className="title-hero">
              Your next obsession,
              <br />
              <span className="accent-text">read before you find it.</span>
            </h1>
            <p className="lede">
              Describe what you love in your own words. SpellScroll turns that into a taste
              signature, searches a vector index of full-colour webtoons, and rebuilds your
              feed every time you react to a card.
            </p>
          </div>

          <div className="row row--wrap">
            <Link className="btn btn--primary btn--lg" href="/onboarding">
              <Icon name="sparkles" /> Start reading
            </Link>
            <Link className="btn btn--lg" href="/archive">
              Browse the archive
            </Link>
          </div>

          <dl className="stat-grid">
            <div className="stat">
              <dd className="stat__value accent-text">{catalog.length}</dd>
              <dt className="stat__label">Series in the archive</dt>
            </div>
            <div className="stat">
              <dd className="stat__value accent-text">{genres.length}</dd>
              <dt className="stat__label">Genres indexed</dt>
            </div>
            <div className="stat">
              <dd className="stat__value accent-text">3</dd>
              <dt className="stat__label">Metadata providers</dt>
            </div>
          </dl>
        </div>

        <div className="cover-wall" aria-hidden="true">
          {columns.map((column, index) => (
            <div className="cover-wall__col" key={index}>
              {[...column, ...column].map((item, i) => (
                <img
                  key={`${item.id}-${i}`}
                  src={item.cover_url}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  width={200}
                  height={300}
                  referrerPolicy="no-referrer"
                />
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="stack-lg" style={{ paddingBlock: 'var(--space-12)' }}>
        <div className="stack">
          <p className="eyebrow">How it works</p>
          <h2 className="title-2">Four agents, one feed</h2>
        </div>
        <div className="feature-grid">
          {[
            {
              icon: 'sparkles',
              title: 'Preference cleaner',
              body: 'Turns a paragraph of plain language into structured genre weights and tone signals.',
            },
            {
              icon: 'search',
              title: 'Vector retriever',
              body: 'Embeds the archive locally and pulls the closest matches by cosine similarity — no API fees.',
            },
            {
              icon: 'scroll',
              title: 'Feed ranker',
              body: 'Balances similarity against colourfulness and popularity, then explains each pick.',
            },
            {
              icon: 'check',
              title: 'Feedback updater',
              body: 'Every rating, skip and finish reshapes your signature before the next cycle.',
            },
          ].map((feature) => (
            <article className="feature" key={feature.title}>
              <div className="feature__icon">
                <Icon name={feature.icon} size={20} />
              </div>
              <h3 className="title-4">{feature.title}</h3>
              <p className="body-sm muted">{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="panel text-center stack"
        style={{ marginBlock: 'var(--space-12) var(--space-20)' }}
      >
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <Logo size="lg" />
        </div>
        <p className="lede">Two minutes of setup, then a feed that keeps learning.</p>
        <div>
          <Link className="btn btn--primary btn--lg" href="/onboarding">
            Attune your taste
          </Link>
        </div>
      </section>
    </div>
  );
}
