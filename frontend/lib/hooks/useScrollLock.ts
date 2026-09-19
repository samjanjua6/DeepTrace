import { useEffect } from "react";

/**
 * Locks `document.body` scroll while `isLocked` is true.
 * Restores the original overflow value on cleanup.
 */
export function useScrollLock(isLocked: boolean) {
  useEffect(() => {
    if (!isLocked) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isLocked]);
}
