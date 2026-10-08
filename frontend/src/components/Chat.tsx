"use client";

import { useCallback, useRef, useState } from "react";

import {
  briefingFromEventData,
  startChat,
  subscribeChatEvents,
} from "@/lib/api";
import type { Asteroid, Briefing, ChatMessage } from "@/lib/types";
import { ApodCard } from "./ApodCard";
import { AsteroidList } from "./AsteroidList";
import { EarthEvents } from "./EarthEvents";
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
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [briefing, setBriefing] = useState<Briefing>(emptyBriefing());
  const unsubRef = useRef<(() => void) | null>(null);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    unsubRef.current?.();
    setBusy(true);
    setStatus("Connecting…");
    setInput("");

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
    };
    const pendingId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: pendingId, role: "assistant", text: "", pending: true },
    ]);

    try {
      const requestId = await startChat(trimmed);
      setStatus(`Request ${requestId.slice(0, 8)}…`);

      unsubRef.current = subscribeChatEvents(requestId, {
        onEvent: (event) => {
          if (event.type === "status") {
            const t = String(event.data.text ?? "");
            if (t) setStatus(t);
          }
          if (event.type === "error") {
            const err = String(event.data.message ?? "Unknown error");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === pendingId
                  ? { ...m, pending: false, error: err, text: err }
                  : m,
              ),
            );
            setStatus("Error");
          }
          if (event.type === "message") {
            const reply = String(event.data.text ?? "");
            const cards = briefingFromEventData(event.data);
            if (cards) setBriefing(cards);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === pendingId
                  ? {
                      ...m,
                      pending: false,
                      text: reply,
                      briefing: cards,
                    }
                  : m,
              ),
            );
            setStatus("Complete");
          }
        },
        onDone: () => {
          setBusy(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === pendingId && m.pending
                ? {
                    ...m,
                    pending: false,
                    text: m.text || "No response received.",
                  }
                : m,
            ),
          );
        },
        onError: (err) => {
          setBusy(false);
          setStatus(err.message);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === pendingId
                ? { ...m, pending: false, error: err.message, text: err.message }
                : m,
            ),
          );
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setBusy(false);
      setStatus(message);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? { ...m, pending: false, error: message, text: message }
            : m,
        ),
      );
    }
  }, [busy]);

  const onAsteroidSelect = (asteroid: Asteroid) => {
    void send(
      `Tell me more about asteroid ${asteroid.name} (id ${asteroid.id}).`,
    );
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <div className="flex min-h-[70vh] flex-col rounded-xl border border-mc-border bg-mc-panel/60">
        <header className="border-b border-mc-border px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-mc-accent">
            Mission Control
          </p>
          <h1 className="text-xl font-semibold">NASA AI Console</h1>
          <p className="text-xs text-mc-muted mt-1">
            {status || "Ready — ask for a briefing or asteroid search."}
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
            disabled={busy}
            placeholder="Ask Mission Commander…"
            className="flex-1 rounded-md border border-mc-border bg-mc-bg px-3 py-2 text-sm outline-none focus:border-mc-accent"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
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
        <p className="text-xs text-mc-muted">
          Card panels are filled from API <code className="font-mono">briefing</code>{" "}
          payloads (Phase 3 will attach structured tool results). Text answers
          come from the Commander via SSE.
        </p>
      </div>
    </div>
  );
}
