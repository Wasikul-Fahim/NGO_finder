import { useCallback, useEffect, useState } from "react";

import { parseError } from "../api/client";

/** Runs `fn` on mount/when deps change; exposes data, loading, error and reload. */
export default function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [tick, setTick] = useState(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: "" }));
    run()
      .then((data) => active && setState({ data, loading: false, error: "" }))
      .catch((err) => active && setState({ data: null, loading: false, error: parseError(err).message }));
    return () => { active = false; };
  }, [run, tick]);

  return { ...state, reload: () => setTick((t) => t + 1) };
}
