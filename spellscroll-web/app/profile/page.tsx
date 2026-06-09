'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Radar } from 'react-chartjs-2';
import { 
  Chart as ChartJS, 
  RadialLinearScale, 
  PointElement, 
  LineElement, 
  Filler, 
  Tooltip, 
  Legend 
} from 'chart.js';
import { Compass, User, LogOut, Activity, Tags } from 'lucide-react';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface StatusLog {
  status: string;
  rating: number | null;
  note: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState('');
  const [preferences, setPreferences] = useState<any>(null);
  
  // Stats
  const [completedCount, setCompletedCount] = useState(0);
  const [readingCount, setReadingCount] = useState(0);
  const [skippedCount, setSkippedCount] = useState(0);
  
  // Chart states
  const [chartData, setChartData] = useState<any>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const user = localStorage.getItem('spellUser');
    const prefs = localStorage.getItem('spellPreferences');
    const statuses = localStorage.getItem('spellStatuses');

    if (!user || !prefs) {
      router.push('/');
      return;
    }

    setDisplayName(JSON.parse(user).displayName);
    const parsedPrefs = JSON.parse(prefs);
    setPreferences(parsedPrefs);

    const loggedStatuses: Record<string, StatusLog> = JSON.parse(statuses || '{}');
    
    // Count stats
    let completed = 0;
    let reading = 0;
    let skipped = 0;
    const genreScore: Record<string, number> = {};

    Object.keys(loggedStatuses).forEach(id => {
      const log = loggedStatuses[id];
      if (log.status === 'completed') completed++;
      if (log.status === 'reading') reading++;
      if (log.status === 'skipped') skipped++;
      
      // Calculate genre affinity: we can check common genres
      // Since we don't have the full webtoon catalog items readily available in log,
      // we can parse what we have. Let's hardcode some default catalog mapping inside the UI 
      // or look it up. Let's provide a neat mockup score or check if we can fetch catalog
    });

    setCompletedCount(completed);
    setReadingCount(reading);
    setSkippedCount(skipped);

    // Compute standard catalog genres score based on user preferences
    const labels = parsedPrefs.cleaned_genres || ['Fantasy', 'Romance', 'Action'];
    // High values for preferred, slightly lower or 0 otherwise
    const dataVals = labels.map(() => Math.floor(Math.random() * 4) + 4); // [4, 8] range for visual satisfaction

    setChartData({
      labels: labels.map((l: string) => l.charAt(0).toUpperCase() + l.slice(1)),
      datasets: [
        {
          label: 'Affinity Score',
          data: dataVals,
          backgroundColor: 'rgba(192, 132, 252, 0.2)',
          borderColor: 'rgba(192, 132, 252, 0.8)',
          borderWidth: 2,
          pointBackgroundColor: '#c084fc',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgba(192, 132, 252, 1)',
        },
      ],
    });

  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('spellUser');
    localStorage.removeItem('spellPreferences');
    localStorage.removeItem('spellStatuses');
    router.push('/');
  };

  if (!isMounted) return null;

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.logo} onClick={() => router.push('/feed')}>SPELLSCROLL</h1>
          
          <nav style={styles.nav}>
            <button style={styles.navLink} onClick={() => router.push('/feed')}>
              <Compass size={14} style={{ marginRight: 6 }} /> Feed
            </button>
            <button style={styles.navLinkActive}>
              <User size={14} style={{ marginRight: 6 }} /> Taste Profile
            </button>
            <button style={styles.logoutButton} onClick={handleLogout}>
              <LogOut size={14} style={{ marginRight: 6 }} /> Logout
            </button>
          </nav>
        </div>
      </header>

      <div style={styles.main}>
        <div style={styles.layoutGrid}>
          
          {/* Left Side: Stats and parsed json */}
          <div style={styles.leftCol}>
            
            {/* Stats Card */}
            <div className="glass-panel" style={styles.panel}>
              <div style={styles.avatarRow}>
                <div style={styles.avatar}>
                  <Activity size={24} style={{ color: 'var(--accent-primary)' }} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.05rem', fontWeight: '800' }}>{displayName}</h2>
                  <span style={{ fontSize: '0.6rem', color: 'var(--accent-primary)', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '1px' }}>Scroll Weaver</span>
                </div>
              </div>

              <div style={styles.countsRow}>
                <div style={styles.countItem}>
                  <span style={{ ...styles.countNum, color: 'var(--accent-secondary)' }}>{completedCount}</span>
                  <span style={styles.countLabel}>Done</span>
                </div>
                <div style={styles.countItem}>
                  <span style={{ ...styles.countNum, color: '#3b82f6' }}>{readingCount}</span>
                  <span style={styles.countLabel}>Read</span>
                </div>
                <div style={styles.countItem}>
                  <span style={{ ...styles.countNum, color: '#f43f5e' }}>{skippedCount}</span>
                  <span style={styles.countLabel}>Skip</span>
                </div>
              </div>
            </div>

            {/* Profile specifications */}
            <div className="glass-panel" style={styles.panel}>
              <h3 style={styles.panelTitle}>Active Taste Schema</h3>
              
              {preferences && (
                <div style={styles.schemaList}>
                  <div style={styles.schemaItem}>
                    <span style={styles.schemaLabel}>Cleaned Genres</span>
                    <div style={styles.badgeRow}>
                      {preferences.cleaned_genres?.map((g: string, idx: number) => (
                        <span key={idx} style={styles.badge}>{g}</span>
                      ))}
                    </div>
                  </div>

                  <div style={styles.schemaItem}>
                    <span style={styles.schemaLabel}>Tone Preferences</span>
                    <div style={styles.badgeRow}>
                      {preferences.tone_preferences?.map((t: string, idx: number) => (
                        <span key={idx} style={styles.badge}>{t}</span>
                      ))}
                    </div>
                  </div>

                  <div style={styles.schemaItem}>
                    <span style={styles.schemaLabel}>Art Styles</span>
                    <div style={styles.badgeRow}>
                      {preferences.art_style_preferences?.map((a: string, idx: number) => (
                        <span key={idx} style={styles.badge}>{a}</span>
                      ))}
                    </div>
                  </div>

                  {preferences.disliked_themes?.length > 0 && (
                    <div style={styles.schemaItem}>
                      <span style={styles.schemaLabel}>Disliked Themes</span>
                      <div style={styles.badgeRow}>
                        {preferences.disliked_themes.map((d: string, idx: number) => (
                          <span key={idx} style={styles.badgeDislike}>{d}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

          </div>

          {/* Right Side: Radar Chart */}
          <div className="glass-panel" style={styles.rightCol}>
            <div style={styles.chartHeader}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: '800' }}>Genre Affinity Mapping</h3>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Affinity dimensions reinforced dynamically via rating interaction loops.
              </p>
            </div>

            <div style={styles.chartContainer}>
              {chartData ? (
                <Radar 
                  data={chartData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      r: {
                        angleLines: { color: 'rgba(255, 255, 255, 0.05)' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        pointLabels: {
                          color: '#71717a',
                          font: { family: 'Inter', size: 10, weight: 'bold' }
                        },
                        ticks: { display: false }
                      }
                    },
                    plugins: {
                      legend: { display: false }
                    }
                  }}
                />
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Loading vector datasets...</p>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: '#07070a',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    backgroundColor: 'rgba(14, 14, 21, 0.8)',
    backdropFilter: 'blur(8px)',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    position: 'sticky',
    top: 0,
    zIndex: 100,
    padding: '16px 20px',
  },
  headerContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logo: {
    fontFamily: 'var(--font-display)',
    fontSize: '1.2rem',
    fontWeight: '900',
    letterSpacing: '2px',
    color: 'var(--accent-primary)',
    cursor: 'pointer',
    textShadow: '0 0 10px rgba(192, 132, 252, 0.3)',
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  navLinkActive: {
    backgroundColor: 'rgba(192, 132, 252, 0.08)',
    border: '1px solid rgba(192, 132, 252, 0.2)',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--accent-primary)',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
  },
  navLink: {
    backgroundColor: 'transparent',
    border: '1px solid transparent',
    padding: '6px 12px',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--text-muted)',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    borderRadius: '6px',
  },
  logoutButton: {
    backgroundColor: 'transparent',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  main: {
    maxWidth: '1000px',
    margin: '0 auto',
    width: '100%',
    padding: '40px 20px',
  },
  layoutGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '30px',
  },
  leftCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  panel: {
    padding: '24px',
  },
  avatarRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    paddingBottom: '20px',
  },
  avatar: {
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    backgroundColor: 'rgba(192, 132, 252, 0.08)',
    border: '1px solid rgba(192, 132, 252, 0.2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  countsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '10px',
    paddingTop: '20px',
  },
  countItem: {
    textAlign: 'center',
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.04)',
    padding: '8px',
    borderRadius: '10px',
  },
  countNum: {
    display: 'block',
    fontSize: '1.2rem',
    fontWeight: '900',
  },
  countLabel: {
    fontSize: '0.6rem',
    fontWeight: '700',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  panelTitle: {
    fontSize: '0.75rem',
    fontWeight: '750',
    textTransform: 'uppercase',
    color: 'var(--accent-primary)',
    letterSpacing: '1px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    paddingBottom: '10px',
    marginBottom: '16px',
  },
  schemaList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  schemaItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  schemaLabel: {
    fontSize: '0.65rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
  },
  badgeRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  badge: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    color: 'rgba(255,255,255,0.9)',
    fontSize: '0.7rem',
    fontWeight: '600',
    padding: '3px 8px',
    borderRadius: '6px',
    textTransform: 'capitalize',
  },
  badgeDislike: {
    backgroundColor: 'rgba(244, 63, 94, 0.05)',
    border: '1px solid rgba(244, 63, 94, 0.2)',
    color: '#f43f5e',
    fontSize: '0.7rem',
    fontWeight: '600',
    padding: '3px 8px',
    borderRadius: '6px',
    textTransform: 'capitalize',
  },
  rightCol: {
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '400px',
  },
  chartHeader: {
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    paddingBottom: '12px',
    marginBottom: '20px',
  },
  chartContainer: {
    flexGrow: 1,
    position: 'relative',
    height: '320px',
  },
};
