/**
 * SpellScroll identity — the React twin of templates/partials/logo.html.
 *
 * An arcane sigil (concave diamond frame around a furled scroll and a spark)
 * beside a Cinzel Decorative wordmark filled with a dark-green -> dark-silver
 * gradient. Kept as real text rather than an image so it stays selectable,
 * translatable and crisp at any size.
 */
export function Logo({ size = 'sm' }: { size?: 'sm' | 'lg' }) {
  const id = `sigil-${size}`;
  return (
    <span className={`logo logo--${size}`} role="img" aria-label="SpellScroll">
      <svg className="logo__sigil" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id={`${id}-stroke`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1f6b4c" />
            <stop offset="52%" stopColor="#7d968a" />
            <stop offset="100%" stopColor="#c9d5ce" />
          </linearGradient>
          <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1f6b4c" stopOpacity="0.38" />
            <stop offset="100%" stopColor="#c9d5ce" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        <path
          d="M24 2c3.6 8.2 13.8 18.4 22 22-8.2 3.6-18.4 13.8-22 22-3.6-8.2-13.8-18.4-22-22C10.2 20.4 20.4 10.2 24 2Z"
          fill={`url(#${id}-fill)`}
          stroke={`url(#${id}-stroke)`}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path
          d="M17.5 17.5h11.2a2.6 2.6 0 0 1 2.6 2.6v9.4a2.6 2.6 0 0 0 2.6 2.6H20.1a2.6 2.6 0 0 1-2.6-2.6v-9.4"
          fill="none"
          stroke={`url(#${id}-stroke)`}
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M17.5 17.5a2.6 2.6 0 0 0 0 5.2h2.6"
          fill="none"
          stroke={`url(#${id}-stroke)`}
          strokeWidth="1.7"
          strokeLinecap="round"
        />
        <path
          d="M22.6 22.7h5.6M22.6 26.4h5.6"
          fill="none"
          stroke="#34d399"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.85"
        />
        <path
          d="m35.4 12.4.9 2.4 2.4.9-2.4.9-.9 2.4-.9-2.4-2.4-.9 2.4-.9Z"
          fill="#c9d5ce"
          opacity="0.9"
        />
      </svg>

      <span className="logo__word">SpellScroll</span>
    </span>
  );
}
