"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { startChat } from "@/lib/api";
import type { AgentEvent } from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8100";

type Options = {
  maxRetries?: number;
};

export function useEventStream(options: Options = {}) {
  const maxRetries = options.maxRetries ?? 2;
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalDurationMs, setTotalDurationMs] = useState<number | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);

  const reset = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setEvents([]);
    setStatus("");
    setError(null);
    setTotalDurationMs(null);
    retriesRef.current = 0;
  }, []);

  const attachSource = useCallback(
    (requestId: string, onMessageText: (text: string, data: Record<string, unknown>) => void) => {
      sourceRef.current?.close();
      const url = `${API_BASE}/api/chat/${requestId}/events`;
      const source = new EventSource(url);
      sourceRef.current = source;

      const forward = (fallbackType: string) => (ev: MessageEvent) => {
        try {
          if (!ev.data || ev.data === "{}") return;
          const parsed = JSON.parse(ev.data) as AgentEvent;
          const event: AgentEvent = {
            ...parsed,
            type: (parsed.type || fallbackType) as AgentEvent["type"],
          };
          setEvents((prev) => [...prev, event]);

          if (event.type === "status" && event.data.text) {
            setStatus(String(event.data.text));
          }
          if (event.type === "error" && event.data.message) {
            setError(String(event.data.message));
          }
          if (event.type === "message") {
            const text = String(event.data.text ?? "");
            if (typeof event.data.duration_ms === "number") {
              setTotalDurationMs(event.data.duration_ms);
            }
            onMessageText(text, event.data);
            setStatus("Complete");
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
        }
      };

      for (const type of [
        "status",
        "agent_start",
        "agent_end",
        "tool_call",
        "tool_result",
        "message",
        "error",
      ]) {
        source.addEventListener(type, forward(type) as EventListener);
      }

      source.addEventListener("done", () => {
        source.close();
        sourceRef.current = null;
        setBusy(false);
      });

      source.onerror = () => {
        source.close();
        sourceRef.current = null;
        if (retriesRef.current < maxRetries) {
          retriesRef.current += 1;
          setStatus(`Reconnecting (${retriesRef.current}/${maxRetries})…`);
          window.setTimeout(() => attachSource(requestId, onMessageText), 500);
          return;
        }
        setBusy(false);
        setError("SSE connection lost");
      };
    },
    [maxRetries],
  );

  const run = useCallback(
    async (
      message: string,
      onMessageText: (text: string, data: Record<string, unknown>) => void,
    ) => {
      reset();
      setBusy(true);
      setStatus("Connecting…");
      try {
        const requestId = await startChat(message);
        setStatus(`Request ${requestId.slice(0, 8)}…`);
        attachSource(requestId, onMessageText);
      } catch (err) {
        setBusy(false);
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [attachSource, reset],
  );

  useEffect(() => () => sourceRef.current?.close(), []);

  return {
    events,
    status,
    busy,
    error,
    totalDurationMs,
    run,
    reset,
  };
}
