import { useState, useEffect, useCallback } from "react";
import { get } from "./api";

export function useFetch<T>(path: string, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    get<T>(path)
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message || "Failed to load"); setLoading(false); });
  }, [path]);

  useEffect(() => { reload(); }, [reload, ...deps]);

  return { data, error, loading, reload };
}
