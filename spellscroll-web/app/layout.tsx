import './globals.css';
import { Inter, Cinzel, Cinzel_Decorative } from 'next/font/google';
import React from 'react';
import type { Metadata, Viewport } from 'next';
import { Icons } from './components/Icons';
import { Header, TabBar } from './components/Header';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const cinzel = Cinzel({
  subsets: ['latin'],
  weight: ['600', '700', '900'],
  variable: '--font-cinzel',
  display: 'swap',
});

// The wordmark face: swashed Roman capitals that read as fantasy calligraphy.
const cinzelDecorative = Cinzel_Decorative({
  subsets: ['latin'],
  weight: ['700', '900'],
  variable: '--font-cinzel-decorative',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'SpellScroll — AI Webtoon Discovery',
  description:
    'A taste-driven reading feed for colourful webtoons, curated by a multi-agent recommendation pipeline.',
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#131b18' },
    { media: '(prefers-color-scheme: light)', color: '#e9eeea' },
  ],
};

/**
 * Applied before first paint so a stored theme choice does not flash the
 * wrong palette. Mirrors the logic in static/js/app.js.
 */
const THEME_BOOTSTRAP = `
(function () {
  try {
    var t = localStorage.getItem('spellscroll_theme');
    if (t) document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${cinzel.variable} ${cinzelDecorative.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <Icons />
        <div className="app-shell">
          <Header />
          <main className="main" id="main">
            {children}
          </main>
          <footer className="footer">
            <div className="container stack-sm">
              <p className="eyebrow">SpellScroll &copy; 2026</p>
              <p className="body-sm muted">
                Metadata and cover art from{' '}
                <a className="accent-text" href="https://anilist.co">
                  AniList
                </a>
                ,{' '}
                <a className="accent-text" href="https://mangadex.org">
                  MangaDex
                </a>{' '}
                and{' '}
                <a className="accent-text" href="https://kitsu.io">
                  Kitsu
                </a>
                .
              </p>
            </div>
          </footer>
          <TabBar />
        </div>
      </body>
    </html>
  );
}
