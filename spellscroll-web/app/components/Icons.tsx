/**
 * Inline SVG sprite, mirroring the one in templates/base.html.
 *
 * Rendered once per document so every `<Icon name="..." />` is a `<use>`
 * reference rather than a duplicated path, and no icon-font CDN is needed.
 */
export function Icons() {
  return (
    <svg width={0} height={0} style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
      <defs>
        <symbol id="i-scroll" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v12a2 2 0 0 0 2 2H8a2 2 0 0 1-2-2V7" />
          <path d="M4 5v2h2" />
          <path d="M9 8h5M9 12h5" />
        </symbol>
        <symbol id="i-tags" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 7v5.2a2 2 0 0 0 .6 1.4l6.8 6.8a2 2 0 0 0 2.8 0l4.6-4.6a2 2 0 0 0 0-2.8l-6.8-6.8A2 2 0 0 0 9.6 5H5a2 2 0 0 0-2 2Z" />
          <circle cx="7.5" cy="9.5" r="1.2" fill="currentColor" stroke="none" />
        </symbol>
        <symbol id="i-sparkles" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="m12 3 1.9 4.9L19 9.8l-5.1 1.9L12 16.6l-1.9-4.9L5 9.8l5.1-1.9Z" />
          <path d="M18 15.5 18.8 18l2.2.9-2.2.9-.8 2.2-.8-2.2-2.2-.9 2.2-.9Z" />
        </symbol>
        <symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.6-3.6" />
        </symbol>
        <symbol id="i-star" viewBox="0 0 24 24" fill="currentColor">
          <path d="m12 2.6 2.9 6.3 6.6.8-4.9 4.6 1.3 6.7L12 17.6l-5.9 3.4 1.3-6.7L2.5 9.7l6.6-.8Z" />
        </symbol>
        <symbol id="i-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5Z" />
          <path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5A2.5 2.5 0 0 1 4 20.5Z" />
        </symbol>
        <symbol id="i-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.1} strokeLinecap="round" strokeLinejoin="round">
          <path d="m4.5 12.5 5 5 10-11" />
        </symbol>
        <symbol id="i-ghost" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 21V9.5a7 7 0 0 1 14 0V21l-2.3-1.8L14.4 21 12 19.2 9.6 21 7.3 19.2Z" />
          <circle cx="9.5" cy="10" r="1" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="10" r="1" fill="currentColor" stroke="none" />
        </symbol>
        <symbol id="i-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <path d="m6 6 12 12M18 6 6 18" />
        </symbol>
        <symbol id="i-alert" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3.5 22 20H2Z" />
          <path d="M12 10v4M12 17h.01" />
        </symbol>
        <symbol id="i-external" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 4h6v6" />
          <path d="M20 4 11 13" />
          <path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" />
        </symbol>
        <symbol id="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
        </symbol>
        <symbol id="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
        </symbol>
        <symbol id="i-refresh" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12a9 9 0 1 1-2.6-6.4" />
          <path d="M21 4v5h-5" />
        </symbol>
      </defs>
    </svg>
  );
}

export function Icon({
  name,
  size = 18,
  className,
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  return (
    <svg width={size} height={size} className={className} aria-hidden="true">
      <use href={`#i-${name}`} />
    </svg>
  );
}
