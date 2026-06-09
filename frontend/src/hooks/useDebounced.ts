import { useEffect, useState } from "react";

// Returns a value that trails the input by delayMs. Used to keep the
// chart panels from refetching (and re-running large simulations on the
// backend) on every keystroke in the inputs form.
export function useDebounced<T>(value: T, delayMs = 400): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}
