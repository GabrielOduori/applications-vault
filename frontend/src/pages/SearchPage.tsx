import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { SearchResult } from '../types';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('all');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.search(query, scope);
      setResults(res.results);
    } catch {
      setResults([]);
    }
    setSearched(true);
    setLoading(false);
  };

  // Security: prevent stored XSS from FTS snippets by escaping all HTML and
  // allowing only <mark> tags for highlighting. This keeps search UX while
  // eliminating script execution vectors from user-controlled content.
  const sanitizeSnippet = (snippet: string) => {
    const escaped = snippet
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return escaped
      .replace(/&lt;mark&gt;/g, '<mark>')
      .replace(/&lt;\/mark&gt;/g, '</mark>');
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900">Search</h2>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search job descriptions, titles, notes..."
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            autoFocus
          />
        </div>
        <select value={scope} onChange={(e) => setScope(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="all">All</option>
          <option value="jobs">Jobs only</option>
          <option value="captures">Captures only</option>
        </select>
        <button type="submit" disabled={loading || !query.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 hover:bg-blue-700">
          Search
        </button>
      </form>

      {loading && <div className="text-center py-8 text-gray-500">Searching...</div>}

      {searched && !loading && results.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No results found for "{query}".
        </div>
      )}

      {results.length > 0 && (
        <div className="bg-white rounded-lg border divide-y">
          {results.map((r, i) => (
            <Link key={i} to={`/jobs/${r.job_id}`} className="block p-4 hover:bg-gray-50">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-gray-900">{r.job_title}</span>
                {r.organisation && <span className="text-sm text-gray-500">at {r.organisation}</span>}
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{r.source}</span>
              </div>
              <p
                className="text-sm text-gray-600"
                dangerouslySetInnerHTML={{ __html: sanitizeSnippet(r.snippet) }}
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
