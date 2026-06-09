'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, ArrowRight, Wand2 } from 'lucide-react';

export default function OnboardingPage() {
  const router = useRouter();
  const [rawInput, setRawInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Weaving interest patterns...');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const activeUser = localStorage.getItem('spellUser');
    if (!activeUser) {
      router.push('/');
    }
  }, [router]);

  const quickSuggestions = [
    'Dark fantasy with slow burn romance',
    'Action-packed isekai with magical systems',
    'Lighthearted comedy slice of life',
    'Avoid gore & tragedy themes',
    'Vibrant artwork with detailed characters'
  ];

  const insertTag = (tag: string) => {
    setRawInput(prev => prev ? `${prev} ${tag}` : tag);
  };

  const handleOnboarding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawInput.trim()) return;

    setLoading(true);
    
    // Rotate loading text
    const loadingTexts = [
      'Extracting taste vector indices...',
      'Matching genres and tones...',
      'Mapping color preferences...',
      'Cerberus NLP aligning configurations...'
    ];
    
    let textIndex = 0;
    const interval = setInterval(() => {
      setLoadingText(loadingTexts[textIndex % loadingTexts.length]);
      textIndex++;
    }, 1500);

    // Rule-based extraction (token optimizer)
    const genresList = ["action", "fantasy", "romance", "comedy", "slice of life", "thriller", "historical", "isekai", "sci-fi", "horror", "drama", "mystery", "superhero"];
    const tonesList = ["slow burn", "dark", "comedy", "fluffy", "intense", "wholesome", "plot twists", "angst", "action-packed"];
    const artStylesList = ["vibrant", "detailed", "webtoon style", "sketchy", "pastel", "minimalist"];
    const dislikesList = ["gore", "mecha", "harem", "tragedy"];

    const rawLower = rawInput.toLowerCase();
    const cleanedGenres = genresList.filter(g => rawLower.includes(g));
    if (cleanedGenres.length === 0) cleanedGenres.push("fantasy", "romance");

    const tonePrefs = tonesList.filter(t => rawLower.includes(t));
    const artPrefs = artStylesList.filter(a => rawLower.includes(a));
    const disliked = dislikesList.filter(d => rawLower.includes(d));

    const preferenceObj = {
      raw_input: rawInput,
      cleaned_genres: cleanedGenres,
      tone_preferences: tonePrefs.length > 0 ? tonePrefs : ["adventurous"],
      art_style_preferences: artPrefs.length > 0 ? artPrefs : ["vibrant"],
      disliked_themes: disliked,
      last_updated: new Date().toISOString()
    };

    // Simulate small latency for UX feel
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    clearInterval(interval);

    // Update localStorage user state
    const activeUser = localStorage.getItem('spellUser');
    if (activeUser) {
      const parsed = JSON.parse(activeUser);
      parsed.onboarded = true;
      localStorage.setItem('spellUser', JSON.stringify(parsed));
      localStorage.setItem('spellPreferences', JSON.stringify(preferenceObj));
      router.push('/feed');
    }
  };

  if (!isMounted) return null;

  return (
    <div style={styles.container}>
      <div className="orb orb-violet pulse-orb" style={{ top: '10%', right: '15%' }} />
      <div className="orb orb-mint pulse-orb" style={{ bottom: '15%', left: '10%', animationDelay: '3s' }} />

      <div className="glass-panel" style={styles.card}>
        {!loading ? (
          <div style={styles.content}>
            <div style={styles.centerHeader}>
              <span style={styles.badge}>Phase 1: Incantation</span>
              <h2 style={styles.title}>Describe Your Perfect Webtoon</h2>
              <p style={styles.subtitle}>Our AI compiler will parse your interests to configure your recommendations.</p>
            </div>

            <form onSubmit={handleOnboarding} style={styles.form}>
              <textarea
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                rows={5}
                style={styles.textarea}
                placeholder="Example: I love dark fantasy stories with slow burn romance and detailed, high-contrast art styles. I absolutely hate tragedy and mecha themes..."
              />

              <div style={styles.suggestionBox}>
                <span style={styles.suggestionTitle}>Insert Suggestion Tags</span>
                <div style={styles.tagGrid}>
                  {quickSuggestions.map((tag, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => insertTag(tag)}
                      style={styles.tag}
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={!rawInput.trim()}
                style={{
                  ...styles.submitButton,
                  opacity: rawInput.trim() ? 1 : 0.5,
                  cursor: rawInput.trim() ? 'pointer' : 'not-allowed'
                }}
              >
                Assemble Recommendations <Wand2 size={16} style={{ marginLeft: 8 }} />
              </button>
            </form>
          </div>
        ) : (
          <div style={styles.loadingBox}>
            <div style={styles.loaderContainer}>
              <div style={styles.loaderOuter}></div>
              <div style={styles.loaderInner}></div>
              <div style={styles.loaderIcon}>
                <Sparkles size={24} style={{ color: 'var(--accent-primary)', animation: 'pulse 1.5s infinite' }} />
              </div>
            </div>
            <h3 style={styles.loadingTitle}>Weaving Your Universe</h3>
            <p style={styles.loadingDesc}>{loadingText}</p>
          </div>
        )}
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
    maxWidth: '600px',
    padding: '40px 30px',
    zIndex: 10,
    boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '25px',
  },
  centerHeader: {
    textAlign: 'center',
  },
  badge: {
    fontSize: '0.6rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '2px',
    color: 'var(--accent-primary)',
    backgroundColor: 'rgba(192, 132, 252, 0.08)',
    border: '1px solid rgba(192, 132, 252, 0.15)',
    padding: '6px 12px',
    borderRadius: '20px',
    display: 'inline-block',
    marginBottom: '15px',
  },
  title: {
    fontSize: '1.6rem',
    fontWeight: '800',
    color: '#fff',
    letterSpacing: '0.5px',
  },
  subtitle: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    marginTop: '6px',
    lineHeight: '1.5',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  textarea: {
    width: '100%',
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '10px',
    padding: '16px',
    color: '#fff',
    fontSize: '0.85rem',
    outline: 'none',
    lineHeight: '1.6',
    resize: 'none',
    transition: 'border-color 0.2s',
  },
  suggestionBox: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  suggestionTitle: {
    fontSize: '0.65rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
  tagGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  tag: {
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.05)',
    color: 'rgba(255,255,255,0.8)',
    fontSize: '0.75rem',
    padding: '6px 14px',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  submitButton: {
    backgroundColor: 'var(--accent-primary)',
    color: '#07070a',
    border: 'none',
    borderRadius: '8px',
    padding: '16px',
    fontSize: '0.9rem',
    fontWeight: '750',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 20px rgba(192, 132, 252, 0.2)',
    transition: 'all 0.2s',
    marginTop: '10px',
  },
  loadingBox: {
    textAlign: 'center',
    padding: '40px 0',
  },
  loaderContainer: {
    position: 'relative',
    width: '80px',
    height: '80px',
    margin: '0 auto 24px auto',
  },
  loaderOuter: {
    position: 'absolute',
    inset: 0,
    borderRadius: '50%',
    border: '4px solid rgba(192, 132, 252, 0.1)',
    borderTopColor: 'var(--accent-primary)',
    animation: 'spin 1.2s linear infinite',
  },
  loaderInner: {
    position: 'absolute',
    inset: '8px',
    borderRadius: '50%',
    border: '4px solid rgba(52, 211, 153, 0.05)',
    borderTopColor: 'var(--accent-secondary)',
    animation: 'spin 1.8s linear infinite reverse',
  },
  loaderIcon: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingTitle: {
    fontSize: '1.1rem',
    fontWeight: '750',
    color: 'var(--accent-primary)',
  },
  loadingDesc: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    marginTop: '6px',
  },
};
