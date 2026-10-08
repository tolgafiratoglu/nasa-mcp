import type { AgentEvent, Briefing } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8100";

export async function startChat(message: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(detail || `Chat failed (${resp.status})`);
  }
  const data = (await resp.json()) as { request_id: string };
  return data.request_id;
}

export type ChatStreamHandlers = {
  onEvent: (event: AgentEvent) => void;
  onDone: () => void;
  onError: (err: Error) => void;
};

/** Subscribe to buffered SSE for a request_id (replays past events). */
export function subscribeChatEvents(
  requestId: string,
  handlers: ChatStreamHandlers,
): () => void {
  const source = new EventSource(
    `${API_BASE}/api/chat/${requestId}/events`,
  );

  const forward = (type: string) => (ev: MessageEvent) => {
    try {
      if (!ev.data || ev.data === "{}") return;
      const parsed = JSON.parse(ev.data) as AgentEvent;
      handlers.onEvent({ ...parsed, type: (parsed.type || type) as AgentEvent["type"] });
    } catch (err) {
      handlers.onError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  for (const type of [
    "status",
    "agent_start",
    "agent_end",
    "tool_call",
    "tool_result",
    "message",
    "error",
  ]) {
    source.addEventListener(type, forward(type) as EventListener);
  }

  source.addEventListener("done", () => {
    source.close();
    handlers.onDone();
  });

  source.onerror = () => {
    source.close();
    handlers.onError(new Error("SSE connection lost"));
  };

  return () => source.close();
}

export function briefingFromEventData(data: Record<string, unknown>): Briefing | null {
  const raw = data.briefing;
  if (!raw || typeof raw !== "object") return null;
  const b = raw as Briefing;
  return {
    asteroids: b.asteroids ?? [],
    space_weather: b.space_weather ?? [],
    earth_events: b.earth_events ?? [],
    apod: b.apod ?? null,
  };
}
