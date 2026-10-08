"use client";

import type { AgentEvent } from "@/lib/types";

type Props = {
  events: AgentEvent[];
  totalDurationMs?: number | null;
};

function label(event: AgentEvent): string {
  switch (event.type) {
    case "agent_start":
      return `${event.agent} started`;
    case "agent_end": {
      const ms = event.data.duration_ms;
      return `${event.agent} finished${typeof ms === "number" ? ` (${ms} ms)` : ""}`;
    }
    case "tool_call":
      return `${event.agent} → ${String(event.data.tool ?? "tool")}`;
    case "tool_result":
      return `${String(event.data.tool ?? "tool")} result (${event.data.ok ? "ok" : "error"})`;
    case "status":
      return String(event.data.text ?? "status");
    case "message":
      return "Final message";
    case "error":
      return String(event.data.message ?? "error");
    default:
      return event.type;
  }
}

export function ExecutionTimeline({ events, totalDurationMs }: Props) {
  return (
    <section className="rounded-lg border border-mc-border bg-mc-panel/80 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-mc-accent">
          Execution
        </h2>
        <span className="font-mono text-xs text-mc-muted">
          {totalDurationMs != null ? `total ${totalDurationMs} ms` : "—"}
        </span>
      </div>
      {events.length === 0 ? (
        <p className="text-sm text-mc-muted">No events yet.</p>
      ) : (
        <ol className="space-y-2 max-h-72 overflow-y-auto">
          {events.map((event, idx) => (
            <li key={`${event.timestamp}-${idx}`} className="flex gap-2 text-xs">
              <span className="font-mono text-mc-muted shrink-0 w-14">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span
                className={
                  "font-mono uppercase tracking-wide shrink-0 w-24 " +
                  (event.type === "error"
                    ? "text-mc-warn"
                    : event.type === "message"
                      ? "text-mc-accent"
                      : "text-mc-muted")
                }
              >
                {event.type}
              </span>
              <span className="text-mc-text/90">{label(event)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
