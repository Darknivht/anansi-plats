"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent, WSEventType } from "@/types";

interface UseWebSocketOptions {
  url?: string;
  token?: string | null;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  onEvent?: (event: WSEvent) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  reconnectAttempts: number;
  send: (type: string, data: unknown) => void;
  subscribe: (eventType: WSEventType, handler: (event: WSEvent) => void) => () => void;
}

export function useWebSocket({
  url,
  token,
  autoReconnect = true,
  maxReconnectAttempts = 10,
  onEvent,
  onConnected,
  onDisconnected,
}: UseWebSocketOptions = {}): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<WSEventType, Set<(event: WSEvent) => void>>>(new Map());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const getWsUrl = useCallback(() => {
    const base = url ?? process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const wsUrl = `${base}/ws/v1`;
    if (token) {
      return `${wsUrl}?token=${encodeURIComponent(token)}`;
    }
    return wsUrl;
  }, [url, token]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setReconnectAttempts(0);
        onConnected?.();
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        onDisconnected?.();

        if (autoReconnect && mountedRef.current) {
          setReconnectAttempts((prev) => {
            const next = prev + 1;
            if (next <= maxReconnectAttempts) {
              const delay = Math.min(1000 * Math.pow(2, next), 30000);
              reconnectTimerRef.current = setTimeout(connect, delay);
            }
            return next;
          });
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WSEvent;
          // Call global handler
          onEvent?.(parsed);
          // Call subscribed handlers
          const typeHandlers = handlersRef.current.get(parsed.type);
          if (typeHandlers) {
            typeHandlers.forEach((handler) => handler(parsed));
          }
        } catch {
          // Ignore malformed messages
        }
      };
    } catch {
      // Connection error handled by onclose
    }
  }, [getWsUrl, autoReconnect, maxReconnectAttempts, onEvent, onConnected, onDisconnected]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const send = useCallback((type: string, data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    }
  }, []);

  const subscribe = useCallback(
    (eventType: WSEventType, handler: (event: WSEvent) => void): (() => void) => {
      if (!handlersRef.current.has(eventType)) {
        handlersRef.current.set(eventType, new Set());
      }
      handlersRef.current.get(eventType)!.add(handler);

      return () => {
        handlersRef.current.get(eventType)?.delete(handler);
      };
    },
    [],
  );

  return {
    isConnected,
    reconnectAttempts,
    send,
    subscribe,
  };
}
