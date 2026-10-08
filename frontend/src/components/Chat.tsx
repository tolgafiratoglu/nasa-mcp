"use client";

import { useCallback, useEffect, useState } from "react";

import { useEventStream } from "@/hooks/useEventStream";
import { briefingFromEventData } from "@/lib/api";
import type { Asteroid, Briefing, ChatMessage } from "@/lib/types";
import { AgentTimeline } from "./AgentTimeline";
import { ApodCard } from "./ApodCard";
import { AsteroidList } from "./AsteroidList";
import { EarthEvents } from "./EarthEvents";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { ToolCallMonitor } from "./ToolCallMonitor";
import { WeatherSummary } from "./WeatherSummary";

const emptyBriefing = (): Briefing => ({
  asteroids: [],
  space_weather: [],
  earth_events: [],
  apod: null,
});

export function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [briefing, setBriefing] = useState<Briefing>(emptyBriefing());
  const [pendingId, setPendingId] = useState<string | null>(null);
  const stream = useEventStream();

  useEffect(() => {
    if (!stream.error || !pendingId) return;
    const err = stream.error;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === pendingId && (m.pending || !m.text)
          ? { ...m, pending: false, error: err, text: err }
          : m,
      ),
    );
    setPendingId(null);
  }, [stream.error, pendingId]);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || stream.busy) return;

      setInput("");
      setBriefing(emptyBriefing());
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        text: trimmed,
      };
      const assistantId = crypto.randomUUID();
      setPendingId(assistantId);
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", text: "", pending: true },
      ]);

      await stream.run(trimmed, (reply, data) => {
        const cards = briefingFromEventData(data);
        if (cards) setBriefing(cards);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, pending: false, text: reply, briefing: cards }
              : m,
          ),
        );
        setPendingId(null);
      });
    },
    [stream],
  );

  const onAsteroidSelect = (asteroid: Asteroid) => {
    void send(
      `Tell me more about asteroid ${asteroid.name} (id ${asteroid.id}).`,
    );
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)_minmax(0,0.95fr)]">
      <div className="space-y-4">
        <AgentTimeline events={stream.events} />
        <ToolCallMonitor events={stream.events} />
        <ExecutionTimeline
          events={stream.events}
          totalDurationMs={stream.totalDurationMs}
        />
      </div>

      <div className="flex min-h-[70vh] flex-col rounded-xl border border-mc-border bg-mc-panel/60">
        <header className="border-b border-mc-border px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-mc-accent">
            Mission Control
          </p>
          <h1 className="text-xl font-semibold">NASA AI Console</h1>
          <p className="text-xs text-mc-muted mt-1">
            {stream.status || "Ready — ask for a briefing or asteroid search."}
          </p>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <p className="text-sm text-mc-muted">
              Try: “Mission briefing for this week” or “Any hazardous asteroids
              approaching Earth?”
            </p>
          ) : null}
          {messages.map((m) => (
            <div
              key={m.id}
              className={
                m.role === "user"
                  ? "ml-8 rounded-lg bg-mc-accent/10 border border-mc-accent/30 px-3 py-2 text-sm"
                  : "mr-8 rounded-lg bg-black/20 border border-mc-border px-3 py-2 text-sm whitespace-pre-wrap"
              }
            >
              {m.pending ? (
                <span className="text-mc-muted animate-pulse">
                  Agents working…
                </span>
              ) : (
                m.text
              )}
            </div>
          ))}
        </div>

        <form
          className="border-t border-mc-border p-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={stream.busy}
            placeholder="Ask Mission Commander…"
            className="flex-1 rounded-md border border-mc-border bg-mc-bg px-3 py-2 text-sm outline-none focus:border-mc-accent"
          />
          <button
            type="submit"
            disabled={stream.busy || !input.trim()}
            className="rounded-md bg-mc-accent px-4 py-2 text-sm font-semibold text-mc-bg disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </div>

      <div className="space-y-4">
        <AsteroidList
          asteroids={briefing.asteroids}
          onSelect={onAsteroidSelect}
        />
        <WeatherSummary events={briefing.space_weather} />
        <EarthEvents events={briefing.earth_events} />
        <ApodCard apod={briefing.apod} />
      </div>
    </div>
  );
}
