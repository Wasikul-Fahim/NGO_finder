import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { apiBaseUrl, getAccessToken } from "../api/client";
import * as notificationApi from "../api/notifications";
import { useAuth } from "./AuthContext";

const NotificationContext = createContext(null);
const POLL_MS = 60_000;
const MAX_BACKOFF_MS = 30_000;

const wsUrl = () => `${apiBaseUrl.replace(/^http/, "ws")}/ws/notifications?token=${encodeURIComponent(getAccessToken() ?? "")}`;

/**
 * Keeps an unread counter and a short "recent" list live. A WebSocket delivers new notifications
 * instantly; if it can't connect (server down, expired token) a 60s poll keeps the counter right,
 * and the REST call also refreshes the access token so the next reconnect succeeds.
 */
export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const [highUnread, setHighUnread] = useState(0);
  const [recent, setRecent] = useState([]);
  const [toast, setToast] = useState(null);
  const [live, setLive] = useState(false);
  const toastTimer = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [count, page] = await Promise.all([notificationApi.unreadCount(), notificationApi.listNotifications({ page_size: 8 })]);
      setUnread(count.unread);
      setHighUnread(count.high_priority_unread);
      setRecent(page.items);
    } catch { /* offline: keep what we have */ }
  }, []);

  useEffect(() => {
    if (!user) { setUnread(0); setHighUnread(0); setRecent([]); setLive(false); return undefined; }
    let closed = false;
    let socket;
    let retry = 0;
    let retryTimer;

    const connect = () => {
      if (closed || !getAccessToken()) return;
      socket = new WebSocket(wsUrl());
      socket.onopen = () => { retry = 0; setLive(true); };
      socket.onmessage = (event) => {
        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }
        if (msg.event === "connected") setUnread(msg.unread);
        if (msg.event === "notification") {
          const n = msg.notification;
          setUnread((c) => c + 1);
          if (n.priority === "HIGH") setHighUnread((c) => c + 1);
          setRecent((list) => [n, ...list.filter((x) => x.id !== n.id)].slice(0, 8));
          setToast(n);
          clearTimeout(toastTimer.current);
          toastTimer.current = setTimeout(() => setToast(null), n.priority === "HIGH" ? 10_000 : 5_000);
        }
      };
      socket.onclose = () => {
        setLive(false);
        if (closed) return;
        retry += 1;
        retryTimer = setTimeout(async () => { await refresh(); connect(); }, Math.min(1000 * 2 ** retry, MAX_BACKOFF_MS));
      };
      socket.onerror = () => socket.close();
    };

    refresh();
    connect();
    const poll = setInterval(refresh, POLL_MS);
    return () => { closed = true; clearInterval(poll); clearTimeout(retryTimer); clearTimeout(toastTimer.current); socket?.close(); };
  }, [user, refresh]);

  const read = useCallback(async (id) => {
    setRecent((list) => list.map((n) => (n.id === id ? { ...n, status: "READ" } : n)));
    try { await notificationApi.markRead(id); } catch { /* refresh below restores truth */ }
    refresh();
  }, [refresh]);

  const readAll = useCallback(async () => {
    try { await notificationApi.markAllRead(); } catch { /* ignore */ }
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ unread, highUnread, recent, live, toast, dismissToast: () => setToast(null), read, readAll, refresh }),
    [unread, highUnread, recent, live, toast, read, readAll, refresh],
  );
  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used inside <NotificationProvider>");
  return ctx;
}
