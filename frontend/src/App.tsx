import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import { CalendarDays, ChevronDown, ChevronRight, Database, Filter, Globe2, MapPinned, RefreshCw, Search } from "lucide-react";
import { fetchDeadlines, fetchInstances, fetchStats } from "./api";
import type { ConferenceInstance, DeadlineEvent, Stats, TabKey } from "./types";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "map", label: "Map" },
  { key: "deadlines", label: "Deadlines" }
];

const categoryColors: Record<string, string> = {
  "AI / Machine Learning": "#2563eb",
  "Algorithms / Theory": "#d97706",
  "Computer Architecture": "#dc2626",
  "Computer Vision": "#16a34a",
  "Database / Data Engineering": "#7c3aed",
  "HCI / Visualization": "#0891b2",
  "Interdiscipline / Emerging": "#65a30d",
  "Networking": "#ea580c",
  "Security / Privacy": "#db2777",
  "Software Engineering": "#059669"
};

const fallbackCategoryColor = "#475569";

function formatDate(value: string | null): string {
  return value ?? "TBD";
}

function hasCoordinates(item: ConferenceInstance): boolean {
  return item.latitude !== null && item.longitude !== null;
}

function isTracking(item: ConferenceInstance): boolean {
  return !hasCoordinates(item);
}

function formatPlace(item: ConferenceInstance): string {
  if (item.city && item.country_ko) return `${item.city}, ${item.country_ko}`;
  if (item.city && item.country) return `${item.city}, ${item.country}`;
  return "Location TBD";
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function deadlineSortValue(item: DeadlineEvent): number {
  if (!item.deadline_date) return Number.MAX_SAFE_INTEGER;
  return new Date(item.deadline_date).getTime();
}

function compareDeadlineTimeline(a: DeadlineEvent, b: DeadlineEvent): number {
  if (a.is_past !== b.is_past) return a.is_past - b.is_past;
  if (!a.is_past) return deadlineSortValue(a) - deadlineSortValue(b);
  return deadlineSortValue(b) - deadlineSortValue(a);
}

function getCategoryColor(name: string): string {
  return categoryColors[name] ?? fallbackCategoryColor;
}

function categoryButtonStyle(name: string, selected: boolean): CSSProperties {
  const color = getCategoryColor(name);
  return {
    "--category-color": color,
    borderColor: selected ? color : undefined,
    backgroundColor: selected ? `${color}18` : undefined,
    color: selected ? color : undefined
  } as CSSProperties;
}

export function App() {
  const [instances, setInstances] = useState<ConferenceInstance[]>([]);
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
    Promise.all([fetchInstances(), fetchDeadlines(), fetchStats()])
      .then(([allItems, deadlineItems, statsData]) => {
        setInstances(allItems);
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
            <p>Ranking-based location and deadline tracking</p>
          </div>
        </header>

        <section className="toolbar">
          <div className="search-row">
            <label className="search">
              <Search size={16} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conference" />
            </label>
            <button
              type="button"
              className="filter-reset"
              onClick={() => setSelectedCategories([])}
              disabled={selectedCategories.length === 0}
              aria-label="Reset category filters"
              title="Reset category filters"
            >
              <RefreshCw size={14} />
              Reset
            </button>
          </div>
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
                className={`category-option ${selectedCategories.includes(name) ? "active" : ""}`}
                style={categoryButtonStyle(name, selectedCategories.includes(name))}
                onClick={() => setSelectedCategories((current) => toggleValue(current, name))}
              >
                <span />
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
              activeTab === "deadlines" ? [] :
              mapItems
            }
            emptyLabel={activeTab === "map" ? "No geocoded conferences yet." : "No matching conferences."}
          />
        )}
      </aside>

      <section className="workspace">
        <div className="statusbar">
          <Metric
            icon={<Database size={18} />}
            label="Conferences"
            value={stats?.conferences ?? 0}
            description="Active conference master records from CCF A/B and KIISE ranked sources."
          />
          <Metric
            icon={<Database size={18} />}
            label="Future instances"
            value={stats?.future_instances ?? instances.length}
            description="Upcoming or TBD yearly conference instances currently loaded in the app."
          />
          <Metric
            icon={<MapPinned size={18} />}
            label="Map-ready"
            value={mapItems.length}
            description="Filtered future instances with latitude and longitude, so they can be drawn on the map."
          />
          <Metric
            icon={<RefreshCw size={18} />}
            label="Unmapped"
            value={trackingItems.length}
            description="Filtered future instances without latitude or longitude, so they cannot be drawn on the map yet."
          />
          <Metric
            icon={<CalendarDays size={18} />}
            label="Deadlines"
            value={deadlineItems.length}
            description="Deadline events matching the current filters, including past events shown dimmed."
          />
        </div>

        {activeTab === "map" ? (
          <MapPanel items={mapItems} />
        ) : (
          <DeadlinePanel items={deadlineItems} />
        )}
      </section>
    </main>
  );
}

function Metric({ icon, label, value, description }: { icon: React.ReactNode; label: string; value: number; description: string }) {
  return (
    <div className="metric" title={description} data-tooltip={description} aria-label={`${label}: ${description}`}>
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
              color: getCategoryColor(item.primary_category),
              fillColor: getCategoryColor(item.primary_category),
              fillOpacity: item.confidence === "low" ? 0.45 : 0.75,
              weight: item.coordinate_precision !== "city" ? 3 : 2
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={0.94}>
              {item.city ? `${item.city}, ${item.country ?? item.country_ko ?? "Unknown"}` : item.country ?? item.country_ko ?? "Unknown"}
            </Tooltip>
            <Popup>
              <strong>{item.abbreviation} {item.year}</strong>
              <br />
              {formatPlace(item)}
              <br />
              {item.confidence} confidence
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      {!items.length && (
        <div className="map-empty">
          Seed data is loaded, but no coordinates are available yet.
        </div>
      )}
    </div>
  );
}

function DeadlinePanel({ items }: { items: DeadlineEvent[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const groups = useMemo(() => {
    const byInstance = new Map<string, DeadlineEvent[]>();
    for (const item of items) {
      byInstance.set(item.instance_id, [...(byInstance.get(item.instance_id) ?? []), item]);
    }
    return Array.from(byInstance.entries())
      .map(([instanceId, groupItems]) => {
        const sortedItems = [...groupItems].sort(compareDeadlineTimeline);
        return {
          instanceId,
          items: sortedItems,
          first: sortedItems[0],
          hasSameDate: new Set(sortedItems.map((item) => item.deadline_date ?? "TBD")).size === 1,
          isPast: sortedItems.every((item) => item.is_past === 1),
        };
      })
      .sort((a, b) => {
        const delta = compareDeadlineTimeline(a.first, b.first);
        if (delta !== 0) return delta;
        return `${a.first.abbreviation} ${a.first.year}`.localeCompare(`${b.first.abbreviation} ${b.first.year}`);
      });
  }, [items]);

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
        <span className="sort-status">Upcoming first</span>
      </div>
      {!items.length ? (
        <div className="notice">No deadline rounds match the filters.</div>
      ) : (
        <div className="deadline-table">
          {groups.map((group) => (
            <article key={group.instanceId} className={`deadline-group ${group.isPast ? "past" : ""}`}>
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
                    <div key={item.deadline_id} className={`deadline-row ${item.is_past === 1 ? "past" : ""}`}>
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
