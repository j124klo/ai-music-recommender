import React, { useState } from 'react';
import { Music, Search, Link as LinkIcon, User, Loader2, AlertCircle, Headphones } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('mood');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Form states
  const [moodText, setMoodText] = useState('');
  const [excludeText, setExcludeText] = useState('');
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [timeRange, setTimeRange] = useState('medium_term');
  const [numResults, setNumResults] = useState(10);

  const handleFetch = async (endpoint, payload) => {
    setLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Wystąpił błąd podczas komunikacji z serwerem.');
      }
      
      setResults(data);
    } catch (err) {
      setError(err.message === 'Failed to fetch' 
        ? 'Błąd połączenia. Upewnij się, że backend działa (start_backend.bat) i ma włączony CORS w main.py.' 
        : err.message);
    } finally {
      setLoading(false);
    }
  };

  const submitMood = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/mood', {
      mood_text: moodText,
      exclude_text: excludeText || null,
      num_results: Number(numResults)
    });
  };

  const submitPlaylist = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/playlist-link', {
      playlist_url: playlistUrl,
      num_results: Number(numResults)
    });
  };

  const submitProfile = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/user-profile', {
      time_range: timeRange,
      num_results: Number(numResults)
    });
  };

  // Convert AI distance to a friendly "Match %" (0.0 is 100%, 1.0 is 0%)
  const calculateMatch = (distance) => {
    const match = Math.max(0, 100 - (distance * 100));
    return match.toFixed(0);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans p-4 md:p-8">
      {/* Header */}
      <header className="max-w-4xl mx-auto mb-10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg shadow-green-500/20">
            <Music className="w-6 h-6 text-gray-950" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Music Recommender</h1>
            <p className="text-gray-400 text-sm">Wektorowy silnik analizy gustu muzycznego</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-8">
        
        {/* Left Column: Controls */}
        <div className="md:col-span-5 space-y-6">
          
          {/* Tabs */}
          <div className="bg-gray-900 rounded-2xl p-2 flex flex-col gap-2 border border-gray-800">
            <button 
              onClick={() => setActiveTab('mood')}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'mood' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}
            >
              <Search className="w-5 h-5" />
              Szukaj po nastroju
            </button>
            <button 
              onClick={() => setActiveTab('playlist')}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'playlist' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}
            >
              <LinkIcon className="w-5 h-5" />
              Z linku do playlisty
            </button>
            <button 
              onClick={() => setActiveTab('profile')}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'profile' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}
            >
              <User className="w-5 h-5" />
              Twój profil Spotify
            </button>
          </div>

          {/* Form Area */}
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 shadow-xl">
            
            {activeTab === 'mood' && (
              <form onSubmit={submitMood} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Opisz swój nastrój</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Czego szukasz?</label>
                  <input 
                    type="text" 
                    required
                    value={moodText}
                    onChange={(e) => setMoodText(e.target.value)}
                    placeholder="np. energiczny rock na siłownię..."
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Czego NIE chcesz? (opcjonalne)</label>
                  <input 
                    type="text" 
                    value={excludeText}
                    onChange={(e) => setExcludeText(e.target.value)}
                    placeholder="np. metal, smutne..."
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
                  />
                </div>
                <div className="pt-2">
                  <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                    Znajdź muzykę
                  </button>
                </div>
              </form>
            )}

            {activeTab === 'playlist' && (
              <form onSubmit={submitPlaylist} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Analiza Twojej playlisty</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Link do playlisty Spotify</label>
                  <input 
                    type="url" 
                    required
                    value={playlistUrl}
                    onChange={(e) => setPlaylistUrl(e.target.value)}
                    placeholder="https://open.spotify.com/playlist/..."
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500"
                  />
                </div>
                <div className="pt-2">
                  <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Music className="w-5 h-5" />}
                    Wygeneruj z playlisty
                  </button>
                </div>
              </form>
            )}

            {activeTab === 'profile' && (
              <form onSubmit={submitProfile} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Twój gust muzyczny</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Na podstawie jakiego okresu?</label>
                  <select 
                    value={timeRange}
                    onChange={(e) => setTimeRange(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500"
                  >
                    <option value="short_term">Ostatnie 4 tygodnie</option>
                    <option value="medium_term">Ostatnie 6 miesięcy</option>
                    <option value="long_term">Cała historia konta</option>
                  </select>
                </div>
                <div className="pt-2">
                  <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <User className="w-5 h-5" />}
                    Analizuj mój profil
                  </button>
                </div>
              </form>
            )}

            {/* Global Settings */}
            <div className="mt-6 pt-6 border-t border-gray-800">
               <label className="flex items-center justify-between text-sm text-gray-400">
                  <span>Liczba wyników</span>
                  <input 
                    type="number" 
                    min="1" max="50"
                    value={numResults}
                    onChange={(e) => setNumResults(e.target.value)}
                    className="w-20 bg-gray-950 border border-gray-700 rounded-lg px-2 py-1 text-white text-center focus:outline-none focus:border-green-500"
                  />
                </label>
            </div>

          </div>
        </div>

        {/* Right Column: Results */}
        <div className="md:col-span-7">
          <div className="bg-gray-900 rounded-2xl p-6 min-h-[500px] border border-gray-800 shadow-xl">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Headphones className="text-green-500" />
              Rekomendacje
            </h2>

            {/* Loading State */}
            {loading && (
              <div className="h-64 flex flex-col items-center justify-center text-green-500 gap-4">
                <Loader2 className="w-10 h-10 animate-spin" />
                <p className="text-gray-400 animate-pulse">Obliczanie wektorów gustu...</p>
              </div>
            )}

            {/* Error State */}
            {!loading && error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-400">
                <AlertCircle className="w-6 h-6 shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            {/* Initial / Empty State */}
            {!loading && !error && !results && (
              <div className="h-64 flex flex-col items-center justify-center text-gray-500 gap-4">
                <Music className="w-12 h-12 opacity-20" />
                <p>Wybierz metodę po lewej i wygeneruj muzykę.</p>
              </div>
            )}

            {/* Results State */}
            {!loading && !error && results && (
              <div className="space-y-4">
                {results.analyzed_tracks_count && (
                  <div className="text-sm text-green-400/80 bg-green-500/10 inline-block px-3 py-1 rounded-full mb-2 border border-green-500/20">
                    Rozpoznano {results.analyzed_tracks_count} utworów bazowych
                  </div>
                )}
                
                <div className="space-y-3">
                  {results.recommendations.map((track, idx) => (
                    <div className="space-y-3">
                  {results.recommendations.map((track, idx) => (
                    <div key={track.id} className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex items-center justify-between hover:border-gray-700 transition-colors group">
                      <div className="flex items-center gap-4">
                        <div className="text-gray-600 font-mono text-sm w-4">{idx + 1}</div>
                        
                        {/* NOWOŚĆ 1: Wskaźnik Koloru Klastra (Pionowy pasek) */}
                        {track.cluster_id && (
                          <div className={`w-1.5 h-10 rounded-full ${
                            track.cluster_id === 1 ? 'bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]' : 
                            track.cluster_id === 2 ? 'bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.5)]' : 
                            track.cluster_id === 3 ? 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]' : 'bg-green-500'
                          }`}></div>
                        )}

                        <div>
                          <div className="text-white font-medium group-hover:text-green-400 transition-colors">
                            {track.title}
                          </div>
                          <div className="text-gray-400 text-sm flex items-center gap-2 mt-1">
                            {track.artist}
                            
                            {/* NOWOŚĆ 2: Odznaka Klastra z opisem */}
                            {track.cluster_id && (
                              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${
                                track.cluster_id === 1 ? 'border-purple-500/30 text-purple-400 bg-purple-500/10' : 
                                track.cluster_id === 2 ? 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10' : 
                                track.cluster_id === 3 ? 'border-yellow-500/30 text-yellow-400 bg-yellow-500/10' : 'border-green-500/30 text-green-400 bg-green-500/10'
                              }`}>
                                Twoje Alter Ego #{track.cluster_id}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-green-500 font-bold">
                          {calculateMatch(track.distance)}%
                        </div>
                        <div className="text-gray-600 text-xs">
                          dopasowania
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}