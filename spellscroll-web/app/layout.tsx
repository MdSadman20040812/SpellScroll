import './globals.css';
import { Inter, Cinzel } from 'next/font/google';
import React from 'react';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-body',
});

const cinzel = Cinzel({
  subsets: ['latin'],
  variable: '--font-display',
});

export const metadata = {
  title: 'SpellScroll — AI Webtoon Discovery Grimoire',
  description: 'A personalized, AI-curated colorful webtoon discovery and tracking platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${cinzel.variable}`}>
      <body>
        <div style={{ position: 'relative', minHeight: '100vh', display: 'flex', flexDirection: 'column', zIndex: 1 }}>
          {/* Main App Container */}
          <main style={{ flexGrow: 1, position: 'relative', zIndex: 10 }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
