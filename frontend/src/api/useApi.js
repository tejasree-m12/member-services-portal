import { useCallback, useEffect, useRef, useState } from "react";

// Loads data when a component appears and whenever `deps` change.
// Returns { data, error, loading, reload }.
//
//   const { data, loading, error } = useApi(() => api.get("/members", { page }), [page]);
export function useApi(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  // Each load gets a number. If the user changes a filter quickly, an older,
  // slower response can arrive after a newer one; the number lets us ignore it.
  const latestRequest = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(() => {
    const requestId = ++latestRequest.current;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    loader()
      .then((data) => {
        if (requestId === latestRequest.current) setState({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (requestId === latestRequest.current) setState({ data: null, error, loading: false });
      });
  }, deps);

  useEffect(() => {
    load();
    return () => {
      latestRequest.current += 1; // component removed: ignore any response still on its way
    };
  }, [load]);

  return { ...state, reload: load };
}
