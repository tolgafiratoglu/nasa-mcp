"use client";

import type { AgentEvent } from "@/lib/types";

type ToolRow = {
  id: string;
  agent: string;
  tool: string;
  arguments?: unknown;
  summary?: string;
  ok?: boolean;
  durationMs?: number | null;
};

function deriveTools(events: AgentEvent[]): ToolRow[] {
  const rows: ToolRow[] = [];
  const open = new Map<string, number>();

  for (const event of events) {
    if (event.type === "tool_call") {
      const tool = String(event.data.tool ?? "tool");
      const key = `${event.agent}:${tool}:${rows.length}`;
      open.set(`${event.agent}:${tool}`, rows.length);
      rows.push({
        id: key,
        agent: event.agent,
        tool,
        arguments: event.data.arguments,
      });
    }
    if (event.type === "tool_result") {
      const tool = String(event.data.tool ?? "tool");
      const idx = open.get(`${event.agent}:${tool}`);
      const target =
        idx != null
          ? rows[idx]
          : {
              id: `${event.agent}:${tool}:result:${rows.length}`,
              agent: event.agent,
              tool,
            };
      if (idx == null) rows.push(target);
      target.summary = String(event.data.summary ?? "");
      target.ok = Boolean(event.data.ok);
      target.durationMs =
        typeof event.data.duration_ms === "number"
          ? event.data.duration_ms
          : null;
    }
  }
  return rows;
}

type Props = { events: AgentEvent[] };

export function ToolCallMonitor({ events }: Props) {
  const rows = deriveTools(events);

  return (
    <section className="rounded-lg border border-mc-border bg-mc-panel/80 p-4">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-mc-accent">
        Tool Calls
      </h2>
      {rows.length === 0 ? (
        <p className="text-sm text-mc-muted">No tool calls yet.</p>
      ) : (
        <ul className="space-y-3 max-h-64 overflow-y-auto">
          {rows.map((row) => (
            <li
              key={row.id}
              className="border-t border-mc-border/50 pt-2 text-sm first:border-0 first:pt-0"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-mc-accent">{row.tool}</span>
                <span
                  className={
                    "rounded px-1.5 py-0.5 text-[10px] uppercase font-mono " +
                    (row.ok === undefined
                      ? "bg-mc-border/40 text-mc-muted"
                      : row.ok
                        ? "bg-mc-accent/20 text-mc-accent"
                        : "bg-mc-warn/20 text-mc-warn")
                  }
                >
                  {row.ok === undefined ? "pending" : row.ok ? "ok" : "error"}
                </span>
              </div>
              <div className="text-xs text-mc-muted mt-1">{row.agent}</div>
              {row.arguments ? (
                <pre className="mt-1 overflow-x-auto rounded bg-black/30 p-2 text-[10px] text-mc-muted">
                  {JSON.stringify(row.arguments, null, 0)}
                </pre>
              ) : null}
              {row.summary ? (
                <p className="mt-1 text-xs text-mc-muted line-clamp-3">
                  {row.summary}
                </p>
              ) : null}
              {row.durationMs != null ? (
                <p className="mt-1 font-mono text-[10px] text-mc-muted">
                  {row.durationMs} ms
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
