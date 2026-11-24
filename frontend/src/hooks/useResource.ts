import { useEffect, useState } from "react";
import { errorMessage, get } from "../services/apiClient";

export function useResource<T>(path: string | null) {
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState<{
    path: string;
    data?: T;
    error?: string;
  }>();
  useEffect(() => {
    if (!path) return;
    let active = true;
    get<T>(path)
      .then((data) => {
        if (active) setResult({ path, data });
      })
      .catch((error) => {
        if (active) setResult({ path, error: errorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return {
    ...(result?.path === path ? result : {}),
    reload: () => setVersion((n) => n + 1),
  };
}
