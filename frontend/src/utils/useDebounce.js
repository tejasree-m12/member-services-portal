import { useEffect, useState } from "react";

// Returns `value` only after it has stopped changing for `delay` ms.
// Used for search boxes so we send one request when the user pauses typing,
// not one request per keystroke.
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
