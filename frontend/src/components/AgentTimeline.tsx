"use client";

import type { AgentEvent } from "@/lib/types";

type AgentState = {
  name: string;
  status: "running" | "done" | "idle";
  durationMs?: number | null;
};

function deriveAgents(events: AgentEvent[]): AgentState[] {
  const order: string[] = [];
  const map = new Map<string, AgentState>();

  for (const event of events) {
    if (event.type !== "agent_start" && event.type !== "agent_end") continue;
    if (!map.has(event.agent)) {
      order.push(event.agent);
      map.set(event.agent, { name: event.agent, status: "idle" });
    }
    const row = map.get(event.agent)!;
    if (event.type === "agent_start") {
      row.status = "running";
    }
    if (event.type === "agent_end") {
      row.status = "done";
      const ms = event.data.duration_ms;
      row.durationMs = typeof ms === "number" ? ms : row.durationMs;
    }
  }
  return order.map((name) => map.get(name)!);
}

type Props = { events: AgentEvent[] };

export function AgentTimeline({ events }: Props) {
  const agents = deriveAgents(events);

  return (
    <section className="rounded-lg border border-mc-border bg-mc-panel/80 p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-mc-accent">
        Agent Timeline
      </h2>
      {agents.length === 0 ? (
        <p className="text-sm text-mc-muted">Waiting for agents…</p>
      ) : (
        <ul className="space-y-2">
          {agents.map((a) => (
            <li
              key={a.name}
              className={
                "flex items-center justify-between rounded border px-3 py-2 text-sm " +
                (a.status === "running"
                  ? "border-mc-accent bg-mc-accent/10"
                  : "border-mc-border/70")
              }
            >
              <div>
                <div className="font-medium font-mono text-xs">{a.name}</div>
                <div className="text-xs text-mc-muted capitalize">{a.status}</div>
              </div>
              <div className="font-mono text-xs text-mc-muted">
                {a.status === "running"
                  ? "…"
                  : a.durationMs != null
                    ? `${a.durationMs} ms`
                    : "—"}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
