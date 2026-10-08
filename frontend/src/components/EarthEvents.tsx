import type { EarthEvent } from "@/lib/types";
import { BriefingCard } from "./BriefingCard";

type Props = { events: EarthEvent[] };

export function EarthEvents({ events }: Props) {
  return (
    <BriefingCard title="Earth Events" empty={events.length === 0}>
      <ul className="space-y-2 text-sm">
        {events.map((e) => (
          <li key={e.id} className="border-t border-mc-border/50 pt-2">
            <div className="font-medium">{e.title}</div>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-mc-muted">
              <span className="font-mono uppercase">{e.status}</span>
              {e.categories.map((c) => (
                <span key={c} className="rounded border border-mc-border px-1.5">
                  {c}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </BriefingCard>
  );
}
