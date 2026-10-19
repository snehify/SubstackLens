
"use client";

import { FormEvent, useEffect, useState } from "react";

type Result = {
  id: number;
  url: string;
  title: string;
  author: string;
  publication: string;
  summary: string;
  published: string;
};

type Publication = {
  name: string;
  post_count: number;
};
type SearchMode = "keyword" | "semantic";

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PAGE_SIZE = 20;

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [publication, setPublication] = useState("");
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
const [searchMode, setSearchMode] = useState<SearchMode>("keyword");

  useEffect(() => {
    async function loadPublications() {
      try {
        const response = await fetch(`${API}/publications`);
        if (!response.ok) {
          throw new Error("Could not load publications.");
        }

        const data = await response.json();
        setPublications(data.publications || []);
      } catch {
        console.error("Could not load publication list.");
      }
    }

    loadPublications();
  }, []);

  async function runSearch(
    searchQuery: string,
    newOffset: number,
    selectedPublication: string,
     selectedMode: SearchMode = searchMode
  ) {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError("");
    setSearched(true);

    const params = new URLSearchParams({
      q: searchQuery.trim(),
      limit: String(PAGE_SIZE),
      offset: String(newOffset),
    });

    if (selectedPublication) {
      params.set("publication", selectedPublication);
    }

    try {
const endpoint =
  selectedMode === "semantic" ? "semantic-search" : "search";

const response = await fetch(`${API}/${endpoint}?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Search API returned an error.");
      }

      const data = await response.json();

      if (data.hint && data.results?.length === 0) {
        throw new Error(data.hint);
      }

      setResults(data.results || []);
      setTotal(data.total ?? data.count ?? 0);
      setOffset(newOffset);
      setHasMore(
        data.has_more ??
          newOffset + (data.results || []).length < (data.total ?? 0)
      );
    } catch (err) {
      setError(
        err instanceof Error && err.message !== "Failed to fetch"
          ? err.message
          : "Could not connect to the API. Start the FastAPI backend on port 8000."
      );
      setResults([]);
      setTotal(0);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }

  function search(e: FormEvent) {
    e.preventDefault();
    runSearch(query, 0, publication);
  }

  function changePublication(value: string) {
    setPublication(value);

    if (searched && query.trim()) {
      runSearch(query, 0, value);
    }
  }

  function changePage(newOffset: number) {
    runSearch(query, newOffset, publication);
  }

  return (
    <main className="shell">
      <nav className="nav">
        
        <span className="navNote">Independent article discovery</span>
      </nav>

      <section className="hero">
        <div className="heroBrand">
  <span className="heroBrandMain">Substack</span>
  <span className="heroBrandAccent">Lens</span>
</div>

        <div className="eyebrow">A SEARCH ENGINE FOR IDEAS</div>
       
        <h1>
          Find the signal
          <br />
          <span>in the newsletters.</span>
        </h1>
        <p className="subhead">
          Search indexed public Substack posts by topic, author,
          publication, and keywords.
        </p>

        <form className="searchForm" onSubmit={search}>
          <span className="searchIcon">⌕</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Try “AI research”, startups, climate..."
            aria-label="Search articles"
          />
          <button type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"} <span>↗</span>
          </button>
        </form>

        <div className="hint">
          Tip: try two or three specific keywords for more focused results.
        </div>

        <div className="filterRow">
         <label htmlFor="search-mode">Search mode</label>

<select
  id="search-mode"
  value={searchMode}
  onChange={(e) => {
    const nextMode = e.target.value as SearchMode;
    setSearchMode(nextMode);

    if (searched && query.trim()) {
      runSearch(query, 0, publication, nextMode);
    }
  }}
  disabled={loading}
>
  <option value="keyword">Keyword search</option>
  <option value="semantic">Semantic search</option>
</select>
          <label htmlFor="publication-filter">Filter by publication</label>
          <select
            id="publication-filter"
            value={publication}
            onChange={(e) => changePublication(e.target.value)}
            disabled={loading}
          >
            <option value="">All publications</option>
            {publications.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name} ({item.post_count})
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="results">
        <div className="resultsHead">
          <div>
            <div className="sectionLabel">DISCOVER</div>
            <h2>
              {searched ? `Results for “${query}”` : "Search across ideas"}
            </h2>
          </div>
          <span className="count">
            {searched
              ? `${total} matching articles`
              : `${publications.length} publications`}
          </span>
        </div>

        {error && <div className="notice">{error}</div>}

        {!searched && (
          <div className="empty">
            <div className="emptyIcon">⌕</div>
            <h3>Your next deep read starts here.</h3>
            <p>
              Search an indexed collection of public newsletter posts.
              Add an RSS feed to the backend to get started.
            </p>
          </div>
        )}

        {loading && (
          <div className="loadingMessage">Searching articles…</div>
        )}

        {searched && !loading && !error && results.length === 0 && (
          <div className="empty">
            <div className="emptyIcon">↗</div>
            <h3>No matches yet</h3>
            <p>
              Try different keywords or choose another publication.
            </p>
          </div>
        )}

        <div className="cards">
          {results.map((r) => (
            <article className="resultCard" key={r.id}>
              <div className="meta">
                <span className="publication">
                  {r.publication || "Substack publication"}
                </span>
                {r.published && <span>{r.published}</span>}
              </div>

              <h3>
                <a href={r.url} target="_blank" rel="noreferrer">
                  {r.title}
                </a>
              </h3>

              {r.summary && <p>{r.summary}</p>}

              <div className="cardFoot">
                <span>
                  {r.author ? `By ${r.author}` : "Public newsletter post"}
                </span>
                <a href={r.url} target="_blank" rel="noreferrer">
                  Read article ↗
                </a>
              </div>
            </article>
          ))}
        </div>

        {searched && !error && total > 0 && (
          <div className="pagination">
            <span className="pageInfo">
              Showing {offset + 1}–{offset + results.length} of {total}
            </span>

            <div className="pageButtons">
              <button
                type="button"
                onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}
                disabled={loading || offset === 0}
              >
                ← Previous
              </button>

              <button
                type="button"
                onClick={() => changePage(offset + PAGE_SIZE)}
                disabled={loading || !hasMore}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </section>

      <footer>
        <span>Built for curious readers.</span>
        <span>
          Only indexed public feed metadata · Not affiliated with Substack
        </span>
      </footer>
    </main>
  );
}
