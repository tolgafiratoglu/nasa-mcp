import type { SpaceWeatherEvent } from "@/lib/types";
import { BriefingCard } from "./BriefingCard";

type Props = { events: SpaceWeatherEvent[] };

export function WeatherSummary({ events }: Props) {
  const counts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.event_type] = (acc[e.event_type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <BriefingCard title="Space Weather" empty={events.length === 0}>
      <ul className="mb-3 flex flex-wrap gap-2 text-xs font-mono">
        {Object.entries(counts).map(([type, n]) => (
          <li
            key={type}
            className="rounded border border-mc-border px-2 py-1 text-mc-accent"
          >
            {type}: {n}
          </li>
        ))}
      </ul>
      <ul className="space-y-2 text-sm">
        {events.slice(0, 8).map((e) => (
          <li key={`${e.event_id}-${e.time}`} className="border-t border-mc-border/50 pt-2">
            <div className="font-medium">
              {e.event_type}{" "}
              <span className="font-mono text-xs text-mc-muted">{e.time}</span>
            </div>
            {e.summary ? (
              <p className="text-mc-muted text-xs mt-1 line-clamp-2">{e.summary}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </BriefingCard>
  );
}
