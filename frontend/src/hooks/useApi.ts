import { useEffect, useState } from 'react';
import { apiRequest } from '../services/api';

export default function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(''); setLoading(true);
    apiRequest<T>(path, { signal: controller.signal }).then(setData).catch(e => {
      if (!controller.signal.aborted) setError(String(e));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [path, version]);
  return { data, error, loading, refresh: () => setVersion(v => v + 1) };
}
