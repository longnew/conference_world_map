export type Confidence = "high" | "medium" | "low";

export type ConferenceInstance = {
  instance_id: string;
  conference_id: string;
  abbreviation: string;
  full_name: string;
  year: number;
  official_website: string | null;
  website_status: string;
  event_status: string;
  start_date: string | null;
  end_date: string | null;
  city: string | null;
  country: string | null;
  country_ko: string | null;
  venue_name: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: string;
  submission_deadline: string | null;
  notification_date: string | null;
  camera_ready_deadline: string | null;
  last_checked_at: string | null;
  next_check_at: string | null;
  confidence: Confidence;
  ranking: {
    ccf?: string;
    kiise?: string;
  };
  secondary_categories: string[];
  source_urls: string[];
  primary_category: string;
  tracking_priority: string;
  purpose_summary: string;
  notes: string | null;
  evidence: Array<{
    field: string;
    value: string;
    source_url: string;
    extracted_at: string;
    confidence: Confidence;
  }>;
};

export type TabKey = "map" | "tracking" | "deadlines" | "recent" | "conflicts" | "archive";

export type DeadlineEvent = {
  deadline_id: string;
  instance_id: string;
  deadline_type: string;
  deadline_date: string | null;
  deadline_time_raw: string | null;
  timezone: string | null;
  comment: string | null;
  source_url: string | null;
  confidence: Confidence;
  year: number;
  abbreviation: string;
  full_name: string;
  primary_category: string;
  ranking: {
    ccf?: string;
    kiise?: string;
  };
};

export type Stats = {
  conferences: number;
  instances: number;
  future_instances: number;
  ccf_ab_conferences: number;
  kiise_ranked_conferences: number;
  map_ready_future: number;
  future_deadlines: number;
};
