'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Icon } from './Icons';
import { Logo } from './Logo';

const NAV = [
  { href: '/feed', label: 'Feed', icon: 'scroll' },
  { href: '/archive', label: 'Archive', icon: 'tags' },
  { href: '/profile', label: 'Essence', icon: 'sparkles' },
];

const THEME_KEY = 'spellscroll_theme';

export function Header() {
  const pathname = usePathname();
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    let stored = '';
    try {
      stored = window.localStorage.getItem(THEME_KEY) || '';
    } catch {
      /* private mode: the theme just does not persist */
    }
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDark(stored ? stored === 'dark' : systemDark);
  }, []);

  function toggleTheme() {
    const next = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      /* ignore */
    }
    setIsDark(!isDark);
  }

  return (
      <header className="header">
        <div className="container header__inner">
          <Link className="brand" href="/">
            <Logo />
          </Link>

          <nav className="nav" aria-label="Primary">
            {NAV.map((item) => (
              <Link
                key={item.href}
                className="nav__link"
                href={item.href}
                aria-current={pathname === item.href ? 'page' : undefined}
              >
                <Icon name={item.icon} size={17} /> {item.label}
              </Link>
            ))}
          </nav>

          <div className="row">
            <button
              className="btn btn--ghost btn--icon"
              type="button"
              onClick={toggleTheme}
              aria-label="Switch colour theme"
            >
              <Icon name={isDark ? 'sun' : 'moon'} />
            </button>
            <Link className="btn btn--sm btn--primary" href="/onboarding">
              Attune
            </Link>
          </div>
        </div>
      </header>
  );
}

/**
 * Bottom tab bar for narrow viewports.
 *
 * Rendered as the last child of the app shell rather than beside the header:
 * it is `position: sticky; bottom: 0`, which only works when it sits after the
 * scrolling content.
 */
export function TabBar() {
  const pathname = usePathname();
  return (
    <nav className="tabbar" aria-label="Primary mobile">
      {NAV.map((item) => (
        <Link
          key={item.href}
          className="tabbar__link"
          href={item.href}
          aria-current={pathname === item.href ? 'page' : undefined}
        >
          <Icon name={item.icon} size={20} />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
