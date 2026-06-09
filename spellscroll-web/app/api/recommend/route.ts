import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Define Cerberus configurations
const CERBERUS_API_KEY = process.env.CERBERUS_API_KEY || "csk-ewm9m3r8mkwwwn2d4kkp8r4wtp8kt66x4hxfp92ec9tyw4rw";
const CERBERUS_API_URL = "https://api.cerberusai.io/v1/chat/completions";

interface WebtoonItem {
  id: string;
  title: string;
  genres: string[];
  colour_rating: number;
  popularity_rank: number;
  mangadex_id: string;
  synopsis: string;
  cover_url: string;
  source_url: string;
  embedding: number[];
}

function calculateLocalRanking(prefs: any, candidates: WebtoonItem[]): any[] {
  const preferredGenres = new Set<string>(prefs.cleaned_genres?.map((g: string) => g.toLowerCase()) || []);
  const dislikedThemes = new Set<string>(prefs.disliked_themes?.map((d: string) => d.toLowerCase()) || []);
  const tonePrefs = new Set<string>(prefs.tone_preferences?.map((t: string) => t.toLowerCase()) || []);

  const scored = candidates.map(item => {
    const itemGenres = item.genres.map(g => g.toLowerCase());
    const itemGenresSet = new Set(itemGenres);

    // Genre similarity matching score
    const intersection = new Set([...preferredGenres].filter(x => itemGenresSet.has(x)));
    const genreScore = preferredGenres.size > 0 ? intersection.size / preferredGenres.size : 0.5;

    // Disliked penalty
    let penalty = 0.0;
    dislikedThemes.forEach(d => {
      if (itemGenresSet.has(d)) {
        penalty = 0.8;
      }
    });

    // Popularity and color scores
    const popularityScore = Math.max(0, 1.0 - (item.popularity_rank / 100.0));
    const colorScore = item.colour_rating;

    // Aggregate score
    const score = (genreScore * 0.5) + (popularityScore * 0.2) + (colorScore * 0.3) - penalty;

    // Build nice human-readable reason
    const matchedArr = Array.from(intersection);
    const reason = matchedArr.length > 0 
      ? `Matches your favorite genres: ${matchedArr.slice(0, 2).join(' & ')}. Vibrant color aesthetics.`
      : "Highly rated colorful webtoon featuring popular storyline elements.";

    return {
      ...item,
      score,
      reason
    };
  });

  // Sort by score descending
  return scored.sort((a, b) => b.score - a.score);
}

export async function POST(request: Request) {
  try {
    const { preferences, interactedIds = [] } = await request.json();
    
    // Load catalog data
    const dataPath = path.join(process.cwd(), 'app', 'api', 'catalog', 'data.json');
    if (!fs.existsSync(dataPath)) {
      return NextResponse.json({ error: 'Database catalog data not found' }, { status: 404 });
    }
    
    const rawData = fs.readFileSync(dataPath, 'utf-8');
    const catalog: WebtoonItem[] = JSON.parse(rawData);

    // Filter out interacted items
    const candidates = catalog.filter(w => !interactedIds.includes(w.id));
    
    if (candidates.length === 0) {
      return NextResponse.json({ webtoons: [] });
    }

    // Run local scoring vector to fetch top candidates
    const scoredCandidates = calculateLocalRanking(preferences, candidates);
    
    // Slice top 10 items for Cerberus API re-ranking (token optimization)
    const topCandidates = scoredCandidates.slice(0, 10);
    
    // Build Cerberus system prompts
    const systemPrompt = 
      "You are a webtoon personalization ranking assistant. " +
      "Rank the candidate webtoons list based on user taste preferences. " +
      "Provide your output as a JSON array of objects, each containing: " +
      "'id' (string matching candidate id), 'rank' (integer, 1 being highest), " +
      "and 'reason' (string, maximum 45 words explaining why it fits the user profile).";

    const promptCandidates = topCandidates.map(item => ({
      id: item.id,
      title: item.title,
      genres: item.genres,
      synopsis: item.synopsis.slice(0, 150)
    }));

    const userPrompt = 
      `User Profile: ${JSON.stringify(preferences)}\n` +
      `Candidate Webtoons list: ${JSON.stringify(promptCandidates)}`;

    let rankedList: any[] = [];
    try {
      const apiResp = await fetch(CERBERUS_API_URL, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${CERBERUS_API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: "cerberus-l3-8b",
          messages: [
            { "role": "system", "content": systemPrompt },
            { "role": "user", "content": userPrompt }
          ],
          temperature: 0.2,
          response_format: { type: "json_object" }
        })
      });

      if (apiResp.ok) {
        const result = await apiResp.json();
        const content = JSON.parse(result.choices[0].message.content);
        
        // Handle variations in JSON structure (array vs wrapper object)
        rankedList = Array.isArray(content) 
          ? content 
          : (content.rankings || content.results || []);
      } else {
        console.error("Cerberus API response error:", await apiResp.text());
      }
    } catch (apiErr) {
      console.error("Cerberus API request failed, executing local fallback ranking:", apiErr);
    }

    // Reconstruct feed matching Cerberus rankings or fall back to local scores
    let finalFeed = [];
    if (rankedList.length > 0) {
      const rankMap = new Map(rankedList.map(r => [r.id, r]));
      
      const ordered = topCandidates
        .filter(item => rankMap.has(item.id))
        .map(item => {
          const r = rankMap.get(item.id);
          return {
            ...item,
            rank: r.rank,
            reason: r.reason || item.reason
          };
        })
        .sort((a, b) => a.rank - b.rank);
        
      // Append remaining items that Cerberus did not return or skipped
      const matchedIds = new Set(ordered.map(o => o.id));
      const remaining = topCandidates.filter(item => !matchedIds.has(item.id));
      finalFeed = [...ordered, ...remaining];
    } else {
      finalFeed = topCandidates;
    }

    // Strip vector embeddings before returning to the web browser
    const sanitized = finalFeed.map(({ embedding, score, ...rest }: any) => rest);
    
    return NextResponse.json({
      webtoons: sanitized
    });

  } catch (error: any) {
    console.error("Recommend Endpoint Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
