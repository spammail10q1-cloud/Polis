import { useEffect, useState, useCallback } from "react";
import { apiFetch, errorMessage } from "./api";

type QueryState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  setData: (data: T | null) => void;
};

export function useQuery<T>(path: string | null, options: { enabled?: boolean } = {}): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path) && options.enabled !== false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const enabled = options.enabled !== false;

  useEffect(() => {
    if (!path || !enabled) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    apiFetch<T>(path)
      .then((result) => {
        if (active) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(errorMessage(err));
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [path, enabled, tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);
  return { data, loading, error, refresh, setData };
}
