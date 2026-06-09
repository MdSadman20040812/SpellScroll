'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Compass, 
  RotateCw, 
  ChevronRight, 
  X, 
  Star, 
  BookOpen, 
  CheckCircle,
  Eye,
  LogOut,
  User,
  Tags
} from 'lucide-react';

interface Webtoon {
  id: string;
  title: string;
  slug: string;
  genres: string[];
  colour_rating: number;
  popularity_rank: number;
  mangadex_id: string;
  synopsis: string;
  cover_url: string;
  source_url: string;
  reason: string;
  status?: string;
}

export default function FeedPage() {
  const router = useRouter();
  const [webtoons, setWebtoons] = useState<Webtoon[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanding, setExpanding] = useState(false);
  const [cycle, setCycle] = useState(1);
  const [activeGenre, setActiveGenre] = useState('all');
  const [availableGenres, setAvailableGenres] = useState<string[]>([]);
  const [displayName, setDisplayName] = useState('');
  const [isMounted, setIsMounted] = useState(false);
  
  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [activeItem, setActiveItem] = useState<Webtoon | null>(null);
  const [modalRating, setModalRating] = useState(5);
  const [modalNote, setModalNote] = useState('');

  useEffect(() => {
    setIsMounted(true);
    const user = localStorage.getItem('spellUser');
    if (!user) {
      router.push('/');
      return;
    }
    setDisplayName(JSON.parse(user).displayName);
    fetchRecommendations();
  }, [router]);

  const fetchRecommendations = async (customInteracted?: string[]) => {
    try {
      setLoading(true);
      const prefs = localStorage.getItem('spellPreferences');
      if (!prefs) return;
      
      const parsedPrefs = JSON.parse(prefs);
      
      // Load interacted IDs from localStorage
      const loggedStatuses = JSON.parse(localStorage.getItem('spellStatuses') || '{}');
      const interacted = customInteracted || Object.keys(loggedStatuses).filter(
        id => loggedStatuses[id].status === 'completed' || loggedStatuses[id].status === 'skipped'
      );

      const resp = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: parsedPrefs,
          interactedIds: interacted
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setWebtoons(data.webtoons || []);
        
        // Extract genres
        const genresSet = new Set<string>();
        (data.webtoons || []).forEach((w: Webtoon) => {
          w.genres.forEach(g => genresSet.add(g.toLowerCase()));
        });
        setAvailableGenres(Array.from(genresSet));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = (webtoonId: string, status: string, rating?: number, note?: string) => {
    const loggedStatuses = JSON.parse(localStorage.getItem('spellStatuses') || '{}');
    loggedStatuses[webtoonId] = {
      status,
      rating: rating || null,
      note: note || '',
      updated_at: new Date().toISOString()
    };
    localStorage.setItem('spellStatuses', JSON.stringify(loggedStatuses));
    
    // Evolve Taste profile in LocalStorage (Reinforcement)
    evolveTasteProfile(webtoonId, status, rating || 3, note || '');
    
    // Update local state instantly
    setWebtoons(prev => prev.map(w => w.id === webtoonId ? { ...w, status } : w));

    // If skipped or completed, trigger feed refresh by filtering it out of active list
    if (status === 'skipped' || status === 'completed') {
      const activeInteracted = Object.keys(loggedStatuses).filter(
        id => loggedStatuses[id].status === 'completed' || loggedStatuses[id].status === 'skipped'
      );
      fetchRecommendations(activeInteracted);
    }
  };

  const evolveTasteProfile = (webtoonId: string, status: string, rating: number, note: string) => {
    const prefs = localStorage.getItem('spellPreferences');
    if (!prefs) return;
    
    const parsed = JSON.parse(prefs);
    const item = webtoons.find(w => w.id === webtoonId);
    if (!item) return;

    const currentGenres = parsed.cleaned_genres || [];
    const currentDislikes = parsed.disliked_themes || [];

    if (status === 'completed' && rating >= 4) {
      // Add positive reinforcement
      item.genres.forEach(g => {
        if (!currentGenres.includes(g)) currentGenres.push(g);
      });
    } else if ((status === 'completed' && rating <= 2) || status === 'skipped') {
      // Add warning/dislike reinforcement
      const primaryGenre = item.genres[0];
      if (primaryGenre && !currentDislikes.includes(primaryGenre)) {
        currentDislikes.push(primaryGenre);
      }
    }

    parsed.cleaned_genres = currentGenres;
    parsed.disliked_themes = currentDislikes;
    parsed.last_updated = new Date().toISOString();
    
    localStorage.setItem('spellPreferences', JSON.stringify(parsed));
  };

  const expandFeed = async () => {
    setExpanding(true);
    setCycle(prev => prev + 1);
    await fetchRecommendations();
    setExpanding(false);
  };

  const openCompletedModal = (item: Webtoon) => {
    setActiveItem(item);
    setModalRating(5);
    setModalNote('');
    setModalOpen(true);
  };

  const submitCompletedFeedback = () => {
    if (!activeItem) return;
    handleStatusUpdate(activeItem.id, 'completed', modalRating, modalNote);
    setModalOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('spellUser');
    localStorage.removeItem('spellPreferences');
    localStorage.removeItem('spellStatuses');
    router.push('/');
  };

  const filteredWebtoons = () => {
    if (activeGenre === 'all') return webtoons;
    return webtoons.filter(w => w.genres.map(g => g.toLowerCase()).includes(activeGenre));
  };

  if (!isMounted) return null;

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.logo} onClick={() => router.push('/feed')}>SPELLSCROLL</h1>
          
          <nav style={styles.nav}>
            <button style={styles.navLinkActive}>
              <Compass size={14} style={{ marginRight: 6 }} /> Feed
            </button>
            <button style={styles.navLink} onClick={() => router.push('/profile')}>
              <User size={14} style={{ marginRight: 6 }} /> Taste Profile
            </button>
            <button style={styles.logoutButton} onClick={handleLogout}>
              <LogOut size={14} style={{ marginRight: 6 }} /> Logout
            </button>
          </nav>
        </div>
      </header>

      <div style={styles.main}>
        {/* Banner */}
        <div className="glass-panel" style={styles.banner}>
          <div style={styles.bannerLeft}>
            <div style={styles.iconCircle}>
              <Compass size={24} style={{ color: 'var(--accent-primary)' }} />
            </div>
            <div>
              <h2 style={styles.bannerTitle}>Your Personal Curation</h2>
              <p style={styles.bannerDesc}>Recommendations computed via client-side vector similarity and re-ranked with Cerberus.</p>
            </div>
          </div>

          <div style={styles.bannerRight}>
            <span style={styles.cycleBadge}>Cycle: {cycle}</span>
            <button onClick={expandFeed} disabled={expanding} style={styles.refreshBtn}>
              <RotateCw size={14} className={expanding ? 'animate-spin' : ''} style={{ marginRight: 6 }} />
              {expanding ? 'Expanding...' : 'Expand feed'}
            </button>
          </div>
        </div>

        {/* Genre Tags */}
        <div style={styles.genreTags}>
          <button 
            onClick={() => setActiveGenre('all')} 
            style={activeGenre === 'all' ? styles.tagActive : styles.tag}
          >
            All Curations
          </button>
          {availableGenres.map((g, idx) => (
            <button 
              key={idx}
              onClick={() => setActiveGenre(g)} 
              style={activeGenre === g ? styles.tagActive : styles.tag}
            >
              {g}
            </button>
          ))}
        </div>

        {/* Loading Spinner */}
        {loading && (
          <div style={styles.loadingBox}>
            <div style={styles.spinner}></div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 12 }}>Consulting the Cerberus Oracle...</p>
          </div>
        )}

        {/* Grid layout */}
        {!loading && filteredWebtoons().length > 0 && (
          <div style={styles.grid}>
            {filteredWebtoons().map(item => (
              <div key={item.id} className="glass-card" style={styles.card}>
                
                {/* Image aspect */}
                <div style={styles.imgContainer}>
                  <img 
                    src={item.cover_url || 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400'} 
                    alt={item.title}
                    style={styles.coverImg}
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400';
                    }}
                  />
                  {/* Status overlays */}
                  {item.status && (
                    <div style={styles.statusOverlay}>
                      <span style={{
                        ...styles.statusTag,
                        backgroundColor: item.status === 'completed' ? 'rgba(52, 211, 153, 0.9)' : 'rgba(59, 130, 246, 0.9)'
                      }}>{item.status}</span>
                    </div>
                  )}
                  {/* Color rating indicator */}
                  <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: '3px',
                    background: `linear-gradient(90deg, var(--accent-primary) ${item.colour_rating * 100}%, transparent 0%)`
                  }} />
                </div>

                {/* Info body */}
                <div style={styles.cardInfo}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
                    {item.genres.slice(0, 2).map((g, idx) => (
                      <span key={idx} style={styles.genreBadge}>{g}</span>
                    ))}
                  </div>

                  <h3 style={styles.cardTitle}>{item.title}</h3>
                  <p style={styles.cardReason}>{item.reason}</p>

                  {/* Actions */}
                  <div style={styles.cardActions}>
                    <button 
                      onClick={() => handleStatusUpdate(item.id, 'skipped')} 
                      style={styles.actionSkip}
                    >
                      <X size={12} style={{ marginRight: 4 }} /> Skip
                    </button>
                    
                    <div style={styles.readDropdownGroup}>
                      <button 
                        onClick={() => handleStatusUpdate(item.id, 'reading')}
                        style={styles.actionRead}
                      >
                        <Eye size={12} style={{ marginRight: 4 }} /> Read
                      </button>
                      <button 
                        onClick={() => openCompletedModal(item)}
                        style={styles.actionComplete}
                      >
                        <CheckCircle size={12} />
                      </button>
                    </div>
                  </div>
                </div>

              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && filteredWebtoons().length === 0 && (
          <div className="glass-panel" style={styles.emptyBox}>
            <Tags size={40} style={{ color: 'var(--text-muted)', marginBottom: 16, opacity: 0.5 }} />
            <h3 style={{ fontSize: '1rem', fontWeight: '750', marginBottom: 6 }}>End of current scroll</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: 280, margin: '0 auto 15px auto', lineHeight: '1.5' }}>
              You have interacted with all recommended items. Expand the discovery grid to pull new candidates.
            </p>
            <button onClick={expandFeed} style={styles.refreshBtn}>
              Expand Catalog Discovery
            </button>
          </div>
        )}
      </div>

      {/* Ratings feedback modal */}
      {modalOpen && (
        <div style={styles.modalBackdrop}>
          <div className="glass-panel" style={styles.modalCard}>
            <div style={styles.modalHeader}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: '750' }}>Review: {activeItem?.title}</h3>
              <button onClick={() => setModalOpen(false)} style={styles.modalCloseBtn}><X size={16} /></button>
            </div>

            <div style={styles.modalBody}>
              {/* Rating selection */}
              <div style={styles.modalField}>
                <label style={styles.modalLabel}>Affinity Rating</label>
                <div style={styles.starRow}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button 
                      key={star}
                      onClick={() => setModalRating(star)}
                      style={styles.starBtn}
                    >
                      <Star 
                        size={22} 
                        fill={star <= modalRating ? '#fbbf24' : 'transparent'} 
                        color={star <= modalRating ? '#fbbf24' : 'rgba(255,255,255,0.2)'} 
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Review notes */}
              <div style={styles.modalField}>
                <label style={styles.modalLabel}>Incantation Review Notes</label>
                <textarea
                  value={modalNote}
                  onChange={(e) => setModalNote(e.target.value)}
                  rows={3}
                  style={styles.modalTextarea}
                  placeholder="Tell the oracle what you enjoyed or disliked about this scroll..."
                />
              </div>

              <div style={styles.modalActions}>
                <button onClick={() => setModalOpen(false)} style={styles.modalCancel}>Cancel</button>
                <button onClick={submitCompletedFeedback} style={styles.modalSave}>Save Review</button>
              </div>
            </div>
          </div>
        </div>
      )}
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
    transition: 'all 0.2s',
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
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
    padding: '30px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '25px',
  },
  banner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px',
    flexWrap: 'wrap',
    gap: '15px',
  },
  bannerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  iconCircle: {
    width: '44px',
    height: '44px',
    borderRadius: '10px',
    backgroundColor: 'rgba(192, 132, 252, 0.08)',
    border: '1px solid rgba(192, 132, 252, 0.15)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bannerTitle: {
    fontSize: '1rem',
    fontWeight: '800',
  },
  bannerDesc: {
    fontSize: '0.7rem',
    color: 'var(--text-muted)',
    marginTop: '2px',
  },
  bannerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  cycleBadge: {
    fontSize: '0.75rem',
    fontWeight: '600',
    border: '1px solid rgba(255,255,255,0.08)',
    backgroundColor: '#07070a',
    padding: '6px 12px',
    borderRadius: '6px',
  },
  refreshBtn: {
    backgroundColor: 'rgba(192, 132, 252, 0.1)',
    border: '1px solid rgba(192, 132, 252, 0.3)',
    color: 'var(--accent-primary)',
    fontWeight: '700',
    fontSize: '0.75rem',
    padding: '7px 14px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'all 0.2s',
  },
  genreTags: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    overflowX: 'auto',
    paddingBottom: '5px',
  },
  tag: {
    backgroundColor: '#161622',
    border: '1px solid rgba(255,255,255,0.03)',
    color: 'var(--text-muted)',
    fontSize: '0.75rem',
    fontWeight: '600',
    padding: '6px 14px',
    borderRadius: '20px',
    cursor: 'pointer',
    textTransform: 'capitalize',
    whiteSpace: 'nowrap',
    transition: 'all 0.2s',
  },
  tagActive: {
    backgroundColor: 'var(--accent-primary)',
    border: '1px solid var(--accent-primary)',
    color: '#07070a',
    fontSize: '0.75rem',
    fontWeight: '750',
    padding: '6px 14px',
    borderRadius: '20px',
    cursor: 'pointer',
    textTransform: 'capitalize',
    whiteSpace: 'nowrap',
  },
  loadingBox: {
    textAlign: 'center',
    padding: '80px 0',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid rgba(192, 132, 252, 0.1)',
    borderTopColor: 'var(--accent-primary)',
    borderRadius: '50%',
    margin: '0 auto',
    animation: 'spin 1s linear infinite',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: '24px',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    position: 'relative',
    height: '100%',
  },
  imgContainer: {
    position: 'relative',
    aspectRatio: '3/4',
    width: '100%',
    backgroundColor: '#07070a',
  },
  coverImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  statusOverlay: {
    position: 'absolute',
    top: '8px',
    right: '8px',
  },
  statusTag: {
    fontSize: '0.55rem',
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    color: '#fff',
    padding: '3px 8px',
    borderRadius: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
  },
  cardInfo: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    flexGrow: 1,
    justifyContent: 'space-between',
  },
  genreBadge: {
    fontSize: '0.55rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    border: '1px solid rgba(255,255,255,0.06)',
    backgroundColor: 'rgba(255,255,255,0.02)',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  cardTitle: {
    fontSize: '0.85rem',
    fontWeight: '800',
    color: '#fff',
    letterSpacing: '0.3px',
    margin: '4px 0',
  },
  cardReason: {
    fontSize: '0.7rem',
    color: 'var(--text-muted)',
    lineHeight: '1.45',
    margin: '8px 0 16px 0',
  },
  cardActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: 'auto',
  },
  actionSkip: {
    flexGrow: 1,
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.05)',
    color: 'var(--text-muted)',
    fontSize: '0.7rem',
    fontWeight: '700',
    padding: '8px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  actionRead: {
    flexGrow: 1,
    backgroundColor: 'rgba(192, 132, 252, 0.06)',
    border: '1px solid rgba(192, 132, 252, 0.2)',
    color: 'var(--accent-primary)',
    fontSize: '0.7rem',
    fontWeight: '700',
    padding: '8px',
    borderRadius: '6px 0 0 6px',
    borderRight: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  actionComplete: {
    backgroundColor: 'rgba(52, 211, 153, 0.08)',
    border: '1px solid rgba(52, 211, 153, 0.2)',
    color: 'var(--accent-secondary)',
    padding: '8px 10px',
    borderRadius: '0 6px 6px 0',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  readDropdownGroup: {
    display: 'flex',
    flexGrow: 1.2,
  },
  emptyBox: {
    textAlign: 'center',
    padding: '50px 20px',
    border: '1px dashed rgba(255,255,255,0.1)',
    borderRadius: '16px',
  },
  modalBackdrop: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(7,7,10,0.85)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    zIndex: 1000,
  },
  modalCard: {
    width: '100%',
    maxWidth: '400px',
    padding: '24px',
    boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    paddingBottom: '12px',
    marginBottom: '16px',
  },
  modalCloseBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  modalBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  modalField: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  modalLabel: {
    fontSize: '0.65rem',
    fontWeight: '700',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    letterSpacing: '0.5px',
  },
  starRow: {
    display: 'flex',
    gap: '8px',
  },
  starBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: 0,
  },
  modalTextarea: {
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '8px',
    padding: '12px',
    color: '#fff',
    fontSize: '0.75rem',
    outline: 'none',
    resize: 'none',
    lineHeight: '1.5',
  },
  modalActions: {
    display: 'flex',
    gap: '10px',
    marginTop: '8px',
  },
  modalCancel: {
    flex: 1,
    backgroundColor: '#07070a',
    border: '1px solid rgba(255,255,255,0.06)',
    color: 'rgba(255,255,255,0.8)',
    fontSize: '0.75rem',
    fontWeight: '600',
    padding: '10px',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  modalSave: {
    flex: 1,
    backgroundColor: 'var(--accent-secondary)',
    color: '#07070a',
    border: 'none',
    fontSize: '0.75rem',
    fontWeight: '700',
    padding: '10px',
    borderRadius: '6px',
    cursor: 'pointer',
    boxShadow: '0 0 10px rgba(52, 211, 153, 0.2)',
  },
};
