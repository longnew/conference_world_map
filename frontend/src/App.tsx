import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { CalendarDays, ChevronDown, ChevronRight, Database, Filter, Globe2, MapPinned, RefreshCw, Search } from "lucide-react";
import { fetchDeadlines, fetchInstances, fetchRecent, fetchStats } from "./api";
import type { ConferenceInstance, DeadlineEvent, Stats, TabKey } from "./types";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "map", label: "Map" },
  { key: "tracking", label: "Tracking" },
  { key: "deadlines", label: "Deadlines" },
  { key: "recent", label: "Recently Updated" },
  { key: "conflicts", label: "Conflicts" },
  { key: "archive", label: "Archive" }
];

const categoryColors: Record<string, string> = {
  "AI / Machine Learning": "#2563eb",
  "Computer Vision": "#16a34a",
  "Computer Architecture": "#dc2626",
  "Database / Data Engineering": "#9333ea"
};

function formatDate(value: string | null): string {
  return value ?? "TBD";
}

function hasCoordinates(item: ConferenceInstance): boolean {
  return item.latitude !== null && item.longitude !== null;
}

function isTracking(item: ConferenceInstance): boolean {
  return !item.venue_name || !hasCoordinates(item);
}

function formatPlace(item: ConferenceInstance): string {
  if (item.venue_name) return item.venue_name;
  if (item.city && item.country_ko) return `${item.city}, ${item.country_ko}`;
  if (item.city && item.country) return `${item.city}, ${item.country}`;
  return "Venue TBD";
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function deadlineSortValue(item: DeadlineEvent): number {
  if (!item.deadline_date) return Number.MAX_SAFE_INTEGER;
  return new Date(item.deadline_date).getTime();
}

export function App() {
  const [instances, setInstances] = useState<ConferenceInstance[]>([]);
  const [recent, setRecent] = useState<ConferenceInstance[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineEvent[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("map");
  const [query, setQuery] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [confidence, setConfidence] = useState("all");
  const [ccf, setCcf] = useState("all");
  const [kiise, setKiise] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchInstances(), fetchRecent(), fetchDeadlines(), fetchStats()])
      .then(([allItems, recentItems, deadlineItems, statsData]) => {
        setInstances(allItems);
        setRecent(recentItems);
        setDeadlines(deadlineItems);
        setStats(statsData);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(
    () => Array.from(new Set(instances.map((item) => item.primary_category))).sort(),
    [instances]
  );

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return instances.filter((item) => {
      const matchesQuery =
        !normalized ||
        item.abbreviation.toLowerCase().includes(normalized) ||
        item.full_name.toLowerCase().includes(normalized) ||
        item.primary_category.toLowerCase().includes(normalized);
      const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(item.primary_category);
      const matchesConfidence = confidence === "all" || item.confidence === confidence;
      const matchesCcf = ccf === "all" || item.ranking.ccf === ccf;
      const matchesKiise = kiise === "all" || item.ranking.kiise === kiise;
      return matchesQuery && matchesCategory && matchesConfidence && matchesCcf && matchesKiise;
    });
  }, [instances, query, selectedCategories, confidence, ccf, kiise]);

  const visibleItems = activeTab === "recent" ? recent : filtered;
  const mapItems = filtered.filter(hasCoordinates);
  const trackingItems = filtered.filter(isTracking);
  const filteredDeadlineIds = new Set(filtered.map((item) => item.instance_id));
  const deadlineItems = deadlines.filter((item) => filteredDeadlineIds.has(item.instance_id));

  return (
    <main className="shell">
      <aside className="sidebar">
        <header className="brand">
          <div className="brand-mark"><Globe2 size={20} /></div>
          <div>
            <h1>AI/CS Conference Tracker</h1>
            <p>Ranking-based venue and deadline tracking</p>
          </div>
        </header>

        <section className="toolbar">
          <label className="search">
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conference" />
          </label>
          <div className="category-filter" aria-label="Category filters">
            <button
              type="button"
              className={selectedCategories.length === 0 ? "active" : ""}
              onClick={() => setSelectedCategories([])}
            >
              All categories
            </button>
            {categories.map((name) => (
              <button
                key={name}
                type="button"
                className={selectedCategories.includes(name) ? "active" : ""}
                onClick={() => setSelectedCategories((current) => toggleValue(current, name))}
              >
                <span style={{ backgroundColor: categoryColors[name] ?? "#0f766e" }} />
                {name}
              </button>
            ))}
          </div>
          <div className="filters">
            <label>
              <Database size={14} />
              <select value={confidence} onChange={(event) => setConfidence(event.target.value)}>
                <option value="all">All confidence</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </label>
            <label>
              <Filter size={14} />
              <select value={ccf} onChange={(event) => setCcf(event.target.value)}>
                <option value="all">All CCF</option>
                <option value="A">CCF A</option>
                <option value="B">CCF B</option>
              </select>
            </label>
            <label>
              <Filter size={14} />
              <select value={kiise} onChange={(event) => setKiise(event.target.value)}>
                <option value="all">All KIISE</option>
                <option value="최우수">최우수</option>
                <option value="우수">우수</option>
              </select>
            </label>
          </div>
        </section>

        <nav className="tabs">
          {tabs.map((tab) => (
            <button key={tab.key} className={activeTab === tab.key ? "active" : ""} onClick={() => setActiveTab(tab.key)}>
              {tab.label}
            </button>
          ))}
        </nav>

        {loading && <div className="notice">Loading tracker data...</div>}
        {error && <div className="notice error">{error}</div>}

        {!loading && !error && (
          <ConferenceList
            items={
              activeTab === "tracking" ? trackingItems :
              activeTab === "deadlines" ? [] :
              activeTab === "map" ? mapItems :
              visibleItems
            }
            emptyLabel={activeTab === "map" ? "No geocoded conferences yet." : "No matching conferences."}
          />
        )}
      </aside>

      <section className="workspace">
        <div className="statusbar">
          <Metric icon={<Database size={18} />} label="Conferences" value={stats?.conferences ?? 0} />
          <Metric icon={<Database size={18} />} label="Future instances" value={stats?.future_instances ?? instances.length} />
          <Metric icon={<MapPinned size={18} />} label="Map-ready" value={mapItems.length} />
          <Metric icon={<RefreshCw size={18} />} label="Tracking" value={trackingItems.length} />
          <Metric icon={<CalendarDays size={18} />} label="Deadlines" value={deadlineItems.length} />
        </div>

        {activeTab === "map" ? (
          <MapPanel items={mapItems} />
        ) : (
          activeTab === "deadlines" ? (
            <DeadlinePanel items={deadlineItems} />
          ) : (
            <DetailPanel tab={activeTab} items={activeTab === "tracking" ? trackingItems : visibleItems} />
          )
        )}
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ConferenceList({ items, emptyLabel }: { items: ConferenceInstance[]; emptyLabel: string }) {
  if (!items.length) return <div className="notice">{emptyLabel}</div>;

  return (
    <div className="list">
      {items.map((item) => (
        <article key={item.instance_id} className="conference-item">
          <div className="item-head">
            <strong>{item.abbreviation} {item.year}</strong>
            <span className={`badge ${item.confidence}`}>{item.confidence}</span>
          </div>
          <p>{item.full_name}</p>
          <dl>
            <dt>Date</dt><dd>{formatDate(item.start_date)} - {formatDate(item.end_date)}</dd>
            <dt>Place</dt><dd>{formatPlace(item)}</dd>
            <dt>Category</dt><dd>{item.primary_category}</dd>
            <dt>Ranking</dt><dd>CCF {item.ranking.ccf ?? "-"} / KIISE {item.ranking.kiise ?? "-"}</dd>
            <dt>Next check</dt><dd>{formatDate(item.next_check_at)}</dd>
          </dl>
        </article>
      ))}
    </div>
  );
}

function MapPanel({ items }: { items: ConferenceInstance[] }) {
  const center: L.LatLngExpression = [20, 0];

  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={2} minZoom={2} scrollWheelZoom className="map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {items.map((item) => (
          <CircleMarker
            key={item.instance_id}
            center={[item.latitude!, item.longitude!]}
            radius={10}
            pathOptions={{
              color: categoryColors[item.primary_category] ?? "#0f766e",
              fillColor: categoryColors[item.primary_category] ?? "#0f766e",
              fillOpacity: item.confidence === "low" ? 0.45 : 0.75,
              weight: item.coordinate_precision === "venue_exact" ? 3 : 2
            }}
          >
            <Popup>
              <strong>{item.abbreviation} {item.year}</strong>
              <br />
              {item.venue_name ?? item.city}
              <br />
              {item.confidence} confidence
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      {!items.length && (
        <div className="map-empty">
          Seed data is loaded, but no venue coordinates are confirmed yet.
        </div>
      )}
    </div>
  );
}

function DetailPanel({ tab, items }: { tab: TabKey; items: ConferenceInstance[] }) {
  return (
    <div className="detail-panel">
      <h2>{tabs.find((item) => item.key === tab)?.label}</h2>
      <ConferenceList items={items} emptyLabel="No items in this view." />
    </div>
  );
}

function DeadlinePanel({ items }: { items: DeadlineEvent[] }) {
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const groups = useMemo(() => {
    const byInstance = new Map<string, DeadlineEvent[]>();
    for (const item of items) {
      byInstance.set(item.instance_id, [...(byInstance.get(item.instance_id) ?? []), item]);
    }
    return Array.from(byInstance.entries())
      .map(([instanceId, groupItems]) => {
        const sortedItems = [...groupItems].sort((a, b) => deadlineSortValue(a) - deadlineSortValue(b));
        return {
          instanceId,
          items: sortedItems,
          first: sortedItems[0],
          hasSameDate: new Set(sortedItems.map((item) => item.deadline_date ?? "TBD")).size === 1,
        };
      })
      .sort((a, b) => {
        const delta = deadlineSortValue(a.first) - deadlineSortValue(b.first);
        return sortDirection === "asc" ? delta : -delta;
      });
  }, [items, sortDirection]);

  const toggleExpanded = (instanceId: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(instanceId)) next.delete(instanceId);
      else next.add(instanceId);
      return next;
    });
  };

  return (
    <div className="detail-panel">
      <div className="panel-head">
        <div>
          <h2>Deadlines</h2>
          <p>Confidence: high = official source verified, medium = tracker source such as ccfddl, low = placeholder or unverified.</p>
        </div>
        <button className="sort-button" type="button" onClick={() => setSortDirection((value) => value === "asc" ? "desc" : "asc")}>
          Date {sortDirection === "asc" ? "oldest first" : "newest first"}
        </button>
      </div>
      {!items.length ? (
        <div className="notice">No upcoming deadline rounds match the filters.</div>
      ) : (
        <div className="deadline-table">
          {groups.map((group) => (
            <article key={group.instanceId} className="deadline-group">
              <button className="deadline-summary" type="button" onClick={() => toggleExpanded(group.instanceId)}>
                {expanded.has(group.instanceId) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                <div>
                  <strong>{group.first.abbreviation} {group.first.year}</strong>
                  <p>{group.first.full_name}</p>
                </div>
                <span>{group.items.length} rounds</span>
                <span>{group.first.deadline_time_raw ?? "TBD"}</span>
                <span className={`badge ${group.first.confidence}`}>{group.first.confidence}</span>
              </button>
              {group.hasSameDate && group.items.length > 1 && (
                <div className="deadline-hint">Abstract/submission rounds share the same date.</div>
              )}
              {expanded.has(group.instanceId) && (
                <div className="deadline-rounds">
                  {group.items.map((item) => (
                    <div key={item.deadline_id} className="deadline-row">
                      <span>{item.deadline_type}</span>
                      <span>{item.deadline_time_raw ?? "TBD"}</span>
                      <span>{item.timezone ?? "-"}</span>
                      <span>{item.comment ?? "-"}</span>
                      <span className={`badge ${item.confidence}`}>{item.confidence}</span>
                      {item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">source</a> : <span>-</span>}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
