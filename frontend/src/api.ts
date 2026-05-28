import type { ConferenceInstance, DeadlineEvent, Stats } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json();
}

export function fetchInstances(): Promise<ConferenceInstance[]> {
  return getJson<ConferenceInstance[]>("/api/instances?future_only=true");
}

export function fetchRecent(): Promise<ConferenceInstance[]> {
  return getJson<ConferenceInstance[]>("/api/updates/recent?days=30");
}

export function fetchDeadlines(): Promise<DeadlineEvent[]> {
  return getJson<DeadlineEvent[]>("/api/deadlines?future_only=true");
}

export function fetchStats(): Promise<Stats> {
  return getJson<Stats>("/api/stats");
}
