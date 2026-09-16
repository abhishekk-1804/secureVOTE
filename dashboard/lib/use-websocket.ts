/**
 * SecureVOTE WebSocket Hook with REST Polling Fallback.
 *
 * Establishes real-time connection using single-use handshake tickets.
 * Gracefully degrades to REST polling when WebSockets are unavailable.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api-client";

export type WebSocketStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "fallback_polling";

export interface WebSocketEventMessage {
  event: string;
  election_id?: string;
  timestamp?: string;
  data?: any;
  user?: string;
  role?: string;
}

interface UseWebSocketOptions {
  electionId?: string | null;
  token?: string | null;
  onEvent?: (message: WebSocketEventMessage) => void;
  pollIntervalMs?: number;
  onPoll?: () => Promise<void> | void;
}

export function useWebSocketElection({
  electionId,
  token,
  onEvent,
  pollIntervalMs = 5000,
  onPoll,
}: UseWebSocketOptions) {
  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<WebSocketEventMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const unmountedRef = useRef(false);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    setStatus("fallback_polling");
    if (onPoll) {
      onPoll();
    }
    pollTimerRef.current = setInterval(() => {
      if (onPoll) {
        onPoll();
      }
    }, pollIntervalMs);
  }, [onPoll, pollIntervalMs]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (!token || !electionId || unmountedRef.current) {
      return;
    }

    try {
      setStatus("connecting");
      // 1. Obtain single-use handshake ticket scoped to this election
      const { ticket } = await api.getWsTicket(token, electionId);

      if (unmountedRef.current) return;


      const wsBase =
        process.env.NEXT_PUBLIC_WS_URL ||
        (process.env.NEXT_PUBLIC_API_URL
          ? process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws")
          : "ws://localhost:8000");

      const wsUrl = `${wsBase}/api/ws/${electionId}?ticket=${encodeURIComponent(
        ticket
      )}`;
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (unmountedRef.current) {
          socket.close();
          return;
        }
        setStatus("connected");
        stopPolling();
      };

      socket.onmessage = (event) => {
        try {
          const parsed: WebSocketEventMessage = JSON.parse(event.data);
          setLastEvent(parsed);
          if (onEvent) {
            onEvent(parsed);
          }
        } catch {
          // Non-JSON message (e.g. heartbeat pong)
        }
      };

      socket.onerror = () => {
        // Fall back to polling on socket error
        startPolling();
      };

      socket.onclose = () => {
        if (unmountedRef.current) return;
        setStatus("disconnected");
        startPolling();
        // Attempt reconnect in 10 seconds
        reconnectTimerRef.current = setTimeout(() => {
          if (!unmountedRef.current) {
            connect();
          }
        }, 10000);
      };
    } catch {
      // Failed to acquire ticket or connect — fall back to polling immediately
      startPolling();
    }
  }, [token, electionId, onEvent, startPolling, stopPolling]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      stopPolling();
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, stopPolling]);

  return {
    status,
    lastEvent,
    reconnect: connect,
  };
}
