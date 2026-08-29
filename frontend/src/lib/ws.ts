import { getToken, wsUrl } from "@/lib/api";

const RECONNECT_DELAY_MS = 3_000;

/** Frames the server pushes. `kind` was added in v2 so one socket can carry both
 *  personal notifications and the lead-status broadcasts the queue listens for. */
export type ServerFrame =
  | ({ kind: "notification" } & Record<string, unknown>)
  | { kind: "lead"; company_id: number; status: string };

type Handler = (frame: ServerFrame) => void;

/** One socket per tab, shared by every subscriber.
 *
 *  The bell used to own the only connection; v2 adds a second listener (the
 *  queue), and opening a socket per component would multiply connections against
 *  a backend whose ConnectionManager holds them all in memory. Reference-counted
 *  instead: the socket opens with the first subscriber and closes with the last.
 */
const handlers = new Set<Handler>();
const resyncHandlers = new Set<() => void>();
const dropHandlers = new Set<() => void>();
/** True once a socket has closed and not yet been replaced -- frames were missed. */
let hadDropped = false;
let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
let closing = false;

function connect() {
  const token = getToken();
  if (!token || socket || closing) return;

  const ws = new WebSocket(wsUrl(`/ws/notifications?token=${encodeURIComponent(token)}`));
  socket = ws;

  ws.onmessage = (event) => {
    let frame: ServerFrame;
    try {
      frame = JSON.parse(event.data);
    } catch {
      return; // a malformed frame must not take the socket down
    }
    for (const handler of handlers) handler(frame);
  };

  ws.onclose = () => {
    // Identity guard. Without it, a *previous* socket's close event -- which
    // arrives after its replacement has already been created -- ran `socket =
    // null`, orphaning the live replacement: nothing held a reference to it any
    // more, so no later unsubscribe could close it, and it stayed registered in
    // the server's ConnectionManager for the life of the tab, being written to
    // on every broadcast. Measured: +1 permanently-open socket per navigation
    // (3 created each time), so a tab that needs one had six after four moves.
    if (socket !== ws) return;
    socket = null;
    hadDropped = true;
    for (const onDrop of dropHandlers) onDrop();
    // Reconnect only while somebody still cares. Every consumer also has a REST
    // path, so a gap here costs freshness, never correctness.
    if (handlers.size > 0 && !closing) {
      reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
    }
  };

  ws.onopen = () => {
    if (socket !== ws) return;
    // A socket that was down missed every frame sent while it was gone, and
    // nothing replays them -- so a listener that only patches state would stay
    // permanently stale. Tell subscribers to re-read from the API instead.
    if (hadDropped) {
      hadDropped = false;
      for (const onResync of resyncHandlers) onResync();
    }
  };
}

export function subscribe(handler: Handler): () => void {
  handlers.add(handler);
  closing = false;
  connect();
  return () => {
    handlers.delete(handler);
    // Deliberately NOT closing when the last subscriber goes. One socket per
    // authenticated tab is the right lifetime: navigating between pages used to
    // tear the socket down and build a new one on every move, which is pure
    // churn (a JWT decode and a handshake each time) and was half of the leak
    // above. `disconnect()` is called explicitly on logout instead -- that call
    // is load-bearing, not hygiene: logout is SPA-only, so without it the next
    // user to log in on this machine inherits the previous user's socket and
    // receives their personal notifications.
  };
}

/** Run `onResync` after the socket comes back from a drop.
 *
 *  A missed frame is otherwise permanent: broadcasts are fire-and-forget with no
 *  replay, so a tab that was briefly offline keeps showing pre-outage state
 *  until something else happens to refetch. */
export function onReconnect(handler: () => void): () => void {
  resyncHandlers.add(handler);
  return () => resyncHandlers.delete(handler);
}

/** Notified when the socket drops, for showing a connection indicator. */
export function onDisconnect(handler: () => void): () => void {
  dropHandlers.add(handler);
  return () => dropHandlers.delete(handler);
}

export function isConnected(): boolean {
  return socket?.readyState === WebSocket.OPEN;
}

/** Close the socket for good. Called on logout so a shared machine does not
 *  hand the next user an authenticated stream belonging to the previous one. */
export function disconnect(): void {
  closing = true;
  clearTimeout(reconnectTimer);
  const ws = socket;
  socket = null;
  ws?.close();
}
