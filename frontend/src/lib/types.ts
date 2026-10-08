/** Mirrors of API / NASA MCP card models (manual; not raw NASA JSON). */

export type CloseApproach = {
  date: string;
  miss_distance_km: number;
  relative_velocity_kmh: number;
};

export type Asteroid = {
  id: string;
  name: string;
  potentially_hazardous: boolean;
  diameter_min_m: number;
  diameter_max_m: number;
  close_approach: CloseApproach | null;
};

export type SpaceWeatherEvent = {
  event_type: string;
  event_id: string;
  time: string;
  summary: string;
};

export type EarthEvent = {
  id: string;
  title: string;
  categories: string[];
  status: string;
};

export type Apod = {
  title: string;
  date: string;
  explanation: string;
  url: string;
  hdurl?: string | null;
  media_type: "image" | "video";
  copyright?: string | null;
};

export type Briefing = {
  asteroids: Asteroid[];
  space_weather: SpaceWeatherEvent[];
  earth_events: EarthEvent[];
  apod: Apod | null;
};

export type AgentEventType =
  | "agent_start"
  | "agent_end"
  | "tool_call"
  | "tool_result"
  | "status"
  | "message"
  | "error";

export type AgentEvent = {
  type: AgentEventType;
  agent: string;
  timestamp: string;
  data: Record<string, unknown>;
  correlation_id: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  briefing?: Briefing | null;
  pending?: boolean;
  error?: string;
};
