import type { Apod } from "@/lib/types";
import { BriefingCard } from "./BriefingCard";

type Props = { apod: Apod | null };

export function ApodCard({ apod }: Props) {
  return (
    <BriefingCard title="Astronomy Picture of the Day" empty={!apod}>
      {apod ? (
        <div className="space-y-3">
          <div>
            <h3 className="text-base font-semibold">{apod.title}</h3>
            <p className="font-mono text-xs text-mc-muted">{apod.date}</p>
          </div>
          {apod.media_type === "image" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={apod.url}
              alt={apod.title}
              className="max-h-64 w-full rounded object-cover border border-mc-border"
            />
          ) : (
            <a
              href={apod.url}
              target="_blank"
              rel="noreferrer"
              className="text-mc-accent underline text-sm"
            >
              Open video
            </a>
          )}
          <p className="text-sm text-mc-muted line-clamp-4">{apod.explanation}</p>
        </div>
      ) : null}
    </BriefingCard>
  );
}
