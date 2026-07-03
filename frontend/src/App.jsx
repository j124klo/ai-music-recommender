import { useState } from 'react';
import { Music, Search, Link as LinkIcon, User, Loader2, AlertCircle, Headphones } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('mood');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const [moodText, setMoodText] = useState('');
  const [excludeText, setExcludeText] = useState('');
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [timeRange, setTimeRange] = useState('medium_term');
  const [numResults, setNumResults] = useState(9); // Domyślnie 9 (ładnie dzieli się na 1, 2 i 3 klastry)

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
      if (!response.ok) throw new Error(data.detail || 'Wystąpił błąd podczas komunikacji z serwerem.');
      setResults(data);
    } catch (err) {
      setError(err.message === 'Failed to fetch' 
        ? 'Błąd połączenia. Upewnij się, że backend działa (start_server.bat).' 
        : err.message);
    } finally {
      setLoading(false);
    }
  };

  const submitMood = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/mood', { mood_text: moodText, exclude_text: excludeText || null, num_results: Number(numResults) });
  };
  const submitPlaylist = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/playlist-link', { playlist_url: playlistUrl, num_results: Number(numResults) });
  };
  const submitProfile = (e) => {
    e.preventDefault();
    handleFetch('/api/recommend/user-profile', { time_range: timeRange, num_results: Number(numResults) });
  };

  const calculateMatch = (distance) => Math.max(0, 100 - (distance * 100)).toFixed(0);

  // Funkcja dobierająca kolory dla poszczególnych klastrów
  const getClusterColor = (id) => {
    switch (id) {
      case 1: return { bg: 'bg-purple-500', text: 'text-purple-400', border: 'border-purple-500/30', shadow: 'shadow-[0_0_8px_rgba(168,85,247,0.5)]' };
      case 2: return { bg: 'bg-cyan-500', text: 'text-cyan-400', border: 'border-cyan-500/30', shadow: 'shadow-[0_0_8px_rgba(6,182,212,0.5)]' };
      case 3: return { bg: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30', shadow: 'shadow-[0_0_8px_rgba(234,179,8,0.5)]' };
      case 4: return { bg: 'bg-pink-500', text: 'text-pink-400', border: 'border-pink-500/30', shadow: 'shadow-[0_0_8px_rgba(236,72,153,0.5)]' };
      case 5: return { bg: 'bg-orange-500', text: 'text-orange-400', border: 'border-orange-500/30', shadow: 'shadow-[0_0_8px_rgba(249,115,22,0.5)]' };
      default: return { bg: 'bg-green-500', text: 'text-green-400', border: 'border-green-500/30', shadow: 'shadow-[0_0_8px_rgba(34,197,94,0.5)]' };
    }
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
            <p className="text-gray-400 text-sm">Wektorowy silnik analizy gustu muzycznego z dynamicznym klastrowaniem</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-8">
        
        {/* Left Column: Controls */}
        <div className="md:col-span-5 space-y-6">
          <div className="bg-gray-900 rounded-2xl p-2 flex flex-col gap-2 border border-gray-800">
            <button onClick={() => setActiveTab('mood')} className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'mood' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}><Search className="w-5 h-5" />Szukaj po nastroju</button>
            <button onClick={() => setActiveTab('playlist')} className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'playlist' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}><LinkIcon className="w-5 h-5" />Z linku do playlisty</button>
            <button onClick={() => setActiveTab('profile')} className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'profile' ? 'bg-gray-800 text-green-400 font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}><User className="w-5 h-5" />Twój profil Spotify</button>
          </div>

          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 shadow-xl">
            {activeTab === 'mood' && (
              <form onSubmit={submitMood} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Opisz swój nastrój</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Czego szukasz?</label>
                  <input type="text" required value={moodText} onChange={(e) => setMoodText(e.target.value)} placeholder="np. energiczny rock..." className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500" />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Czego NIE chcesz?</label>
                  <input type="text" value={excludeText} onChange={(e) => setExcludeText(e.target.value)} placeholder="np. metal, smutne..." className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-red-500" />
                </div>
                <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">{loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}Znajdź muzykę</button>
              </form>
            )}

            {activeTab === 'playlist' && (
              <form onSubmit={submitPlaylist} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Analiza Twojej playlisty</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Link do playlisty</label>
                  <input type="url" required value={playlistUrl} onChange={(e) => setPlaylistUrl(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500" />
                </div>
                <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">{loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Music className="w-5 h-5" />}Wygeneruj z playlisty</button>
              </form>
            )}

            {activeTab === 'profile' && (
              <form onSubmit={submitProfile} className="space-y-4">
                <h2 className="text-lg font-semibold text-white mb-4">Twój gust muzyczny</h2>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Okres</label>
                  <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-green-500">
                    <option value="short_term">Ostatnie 4 tygodnie</option>
                    <option value="medium_term">Ostatnie 6 miesięcy</option>
                    <option value="long_term">Cała historia konta</option>
                  </select>
                </div>
                <button type="submit" disabled={loading} className="w-full bg-green-500 hover:bg-green-400 text-gray-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">{loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <User className="w-5 h-5" />}Analizuj mój profil</button>
              </form>
            )}

            <div className="mt-6 pt-6 border-t border-gray-800">
               <label className="flex items-center justify-between text-sm text-gray-400">
                  <span>Łączna liczba wyników</span>
                  <input type="number" min="1" max="50" value={numResults} onChange={(e) => setNumResults(e.target.value)} className="w-20 bg-gray-950 border border-gray-700 rounded-lg px-2 py-1 text-white text-center focus:outline-none focus:border-green-500" />
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

            {loading && (
              <div className="h-64 flex flex-col items-center justify-center text-green-500 gap-4">
                <Loader2 className="w-10 h-10 animate-spin" />
                <p className="text-gray-400 animate-pulse">Analiza klastrów i wektorów gustu...</p>
              </div>
            )}

            {!loading && error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-400">
                <AlertCircle className="w-6 h-6 shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            {!loading && !error && !results && (
              <div className="h-64 flex flex-col items-center justify-center text-gray-500 gap-4">
                <Music className="w-12 h-12 opacity-20" />
                <p>Wybierz metodę po lewej i wygeneruj muzykę.</p>
              </div>
            )}

            {/* Renderowanie Wyników i Klastrów */}
            {!loading && !error && results && results.clusters && (
              <div className="space-y-8">
                
                {/* Informacyjny Header */}
                {activeTab !== 'mood' && results.clusters[0]?.cluster_id !== null && (
                   <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 mb-6">
                      <p className="text-blue-400 font-medium text-sm">
                        Rozpoznano <span className="font-bold text-white text-lg mx-1">{results.clusters.length}</span> typów muzyki w Twoim guście! 
                      </p>
                      <p className="text-gray-400 text-xs mt-1">Oto rekomendacje pogrupowane na podstawie wykrytych nurtów.</p>
                   </div>
                )}

                {/* Lista Klastrów */}
                {results.clusters.map((cluster) => {
                  const colors = getClusterColor(cluster.cluster_id);
                  
                  return (
                    <div key={cluster.cluster_id || 'mood'} className="space-y-3">
                      
                      {/* Nagłówek Grupy Klastra */}
                      {cluster.cluster_id && (
                        <h3 className={`text-sm font-bold uppercase tracking-wider mb-3 flex items-center gap-2 ${colors.text}`}>
                          <div className={`w-3 h-3 rounded-full ${colors.bg} ${colors.shadow}`}></div>
                          Twoje Alter Ego #{cluster.cluster_id}
                        </h3>
                      )}
                      
                      {/* Piosenki wewnątrz klastra */}
                      {cluster.recommendations.map((track, idx) => (
                        <div key={track.id} className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex items-center justify-between hover:border-gray-700 transition-colors group">
                          <div className="flex items-center gap-4">
                            <div className="text-gray-600 font-mono text-sm w-4">{idx + 1}</div>
                            
                            {/* Wskaźnik koloru */}
                            {cluster.cluster_id && (
                              <div className={`w-1 h-8 rounded-full ${colors.bg}`}></div>
                            )}

                            <div>
                              <div className="text-white font-medium group-hover:text-green-400 transition-colors">
                                {track.title}
                              </div>
                              <div className="text-gray-400 text-sm mt-0.5">
                                {track.artist}
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
                  );
                })}
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}