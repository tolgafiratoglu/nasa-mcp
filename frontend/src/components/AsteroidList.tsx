import type { Asteroid } from "@/lib/types";
import { BriefingCard } from "./BriefingCard";

type Props = {
  asteroids: Asteroid[];
  onSelect?: (asteroid: Asteroid) => void;
};

export function AsteroidList({ asteroids, onSelect }: Props) {
  return (
    <BriefingCard title="Asteroids" empty={asteroids.length === 0}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-mc-muted">
            <tr>
              <th className="pb-2 pr-3 font-medium">Name</th>
              <th className="pb-2 pr-3 font-medium">PHA</th>
              <th className="pb-2 font-medium">Miss (km)</th>
            </tr>
          </thead>
          <tbody>
            {asteroids.map((a) => (
              <tr
                key={a.id}
                className="border-t border-mc-border/60 hover:bg-white/5 cursor-pointer"
                onClick={() => onSelect?.(a)}
              >
                <td className="py-2 pr-3">
                  <div className="font-medium">{a.name}</div>
                  <div className="font-mono text-xs text-mc-muted">{a.id}</div>
                </td>
                <td className="py-2 pr-3">
                  {a.potentially_hazardous ? (
                    <span className="text-mc-warn">Yes</span>
                  ) : (
                    "No"
                  )}
                </td>
                <td className="py-2 font-mono text-xs">
                  {a.close_approach
                    ? a.close_approach.miss_distance_km.toLocaleString()
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </BriefingCard>
  );
}
