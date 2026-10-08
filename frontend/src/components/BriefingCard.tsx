import type { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
  empty?: boolean;
  emptyLabel?: string;
};

export function BriefingCard({
  title,
  children,
  empty,
  emptyLabel = "No data for this briefing yet.",
}: Props) {
  return (
    <section className="rounded-lg border border-mc-border bg-mc-panel/80 p-4 shadow-sm">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-mc-accent">
        {title}
      </h2>
      {empty ? (
        <p className="text-sm text-mc-muted">{emptyLabel}</p>
      ) : (
        children
      )}
    </section>
  );
}
