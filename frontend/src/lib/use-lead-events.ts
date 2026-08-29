import { useEffect, useRef } from "react";
import { subscribe } from "@/lib/ws";

const COALESCE_MS = 400;

/** Re-run `onChange` whenever any lead changes hands anywhere (FR-15).
 *
 *  A busy team generates bursts of these, so calls are coalesced into one
 *  refresh rather than one request per frame. The handler is held in a ref so a
 *  caller that rebuilds its callback each render does not churn the subscription.
 */
export function useLeadEvents(onChange: () => void) {
  const latest = useRef(onChange);
  latest.current = onChange;

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = subscribe((frame) => {
      if (frame.kind !== "lead") return;
      clearTimeout(timer);
      timer = setTimeout(() => latest.current(), COALESCE_MS);
    });
    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, []);
}
