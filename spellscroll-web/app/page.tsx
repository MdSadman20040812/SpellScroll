'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { BookOpen, Sparkles } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    // Auto redirect if already logged in
    const activeUser = localStorage.getItem('spellUser');
    if (activeUser) {
      const parsed = JSON.parse(activeUser);
      if (parsed.onboarded) {
        router.push('/feed');
      } else {
        router.push('/onboarding');
      }
    }
  }, [router]);

  const handleEnter = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim()) return;

    const userObj = {
      username: username.trim(),
      email: email.trim(),
      displayName: displayName.trim() || username.trim(),
      onboarded: false,
    };

    localStorage.setItem('spellUser', JSON.stringify(userObj));
    router.push('/onboarding');
  };

  if (!isMounted) return null;

  return (
    <div style={styles.container}>
      {/* Background Neon Orbs */}
      <div className="orb orb-violet pulse-orb" style={{ top: '20%', left: '20%' }} />
      <div className="orb orb-mint pulse-orb" style={{ bottom: '20%', right: '20%', animationDelay: '2s' }} />

      <div className="glass-panel" style={styles.card}>
        <div style={styles.header}>
          <h1 style={styles.title} className="text-neon-violet">
            SPELLSCROLL
          </h1>
          <p style={styles.subtitle}>AI-CURATED COLORFUL WEBTOON DISCOVERY</p>
        </div>

        <form onSubmit={handleEnter} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Arcane Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. spellweaver"
              style={styles.input}
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. weaver@scroll.local"
              style={styles.input}
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Display Name (Optional)</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Master Weaver"
              style={styles.input}
            />
          </div>

          <button type="submit" style={styles.button}>
            Unlock Grimoire <Sparkles size={16} style={{ marginLeft: 8 }} />
          </button>
        </form>

        <div style={styles.badgeContainer}>
          <span style={styles.badge}>
            Vercel Serverless Ready
          </span>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    backgroundColor: '#07070a',
    zIndex: 1,
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    padding: '40px 30px',
    zIndex: 10,
    boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
  },
  header: {
    textAlign: 'center',
    marginBottom: '35px',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '2.5rem',
    fontWeight: '900',
    letterSpacing: '4px',
    marginBottom: '6px',
  },
  subtitle: {
    fontSize: '0.65rem',
    fontWeight: '700',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    fontSize: '0.7rem',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    color: 'var(--text-muted)',
  },
  input: {
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '8px',
    padding: '12px 16px',
    color: '#fff',
    fontSize: '0.85rem',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  button: {
    backgroundColor: 'var(--accent-primary)',
    color: '#07070a',
    border: 'none',
    borderRadius: '8px',
    padding: '14px',
    fontSize: '0.9rem',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 15px rgba(192, 132, 252, 0.3)',
    transition: 'opacity 0.2s',
    marginTop: '10px',
  },
  badgeContainer: {
    textAlign: 'center',
    marginTop: '25px',
  },
  badge: {
    fontSize: '0.6rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
    color: 'var(--accent-secondary)',
    border: '1px solid rgba(52, 211, 153, 0.2)',
    padding: '4px 10px',
    borderRadius: '20px',
    backgroundColor: 'rgba(52, 211, 153, 0.05)',
  },
};
