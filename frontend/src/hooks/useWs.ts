import { useEffect, useState } from 'react';
import type { WsMessage } from '../api/types';

export function useWs(aoiId?: string) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WsMessage[]>([]);

  useEffect(() => {
    if (import.meta.env.VITE_ENABLE_MSW === 'true') {
      setConnected(false);
      return;
    }
    let cancelled = false;
    let retry = 1000;
    let socket: WebSocket | null = null;

    const connect = () => {
      const base = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws').replace(/\/api$/, '');
      socket = new WebSocket(`${base}/ws/alerts`);
      socket.onopen = () => {
        setConnected(true);
        retry = 1000;
        socket?.send(JSON.stringify({ subscribe: aoiId ? { aoi_id: aoiId } : {} }));
      };
      socket.onmessage = (event) => setMessages((items) => [JSON.parse(event.data), ...items].slice(0, 3));
      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          window.setTimeout(connect, retry);
          retry = Math.min(retry * 2, 30_000);
        }
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [aoiId]);

  return { connected, messages };
}
