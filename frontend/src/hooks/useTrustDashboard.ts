"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { TrustDashboardResponse } from "@/types/api";

interface DashboardState {
  data: TrustDashboardResponse | null;
  loading: boolean;
  error: string | null;
}

/** Fetches Trust Dashboard stats on mount, with a manual `refresh()` for
 * the dashboard page's refresh button — no polling by default, since
 * these stats only change when someone runs a new query elsewhere in
 * the app. */
export function useTrustDashboard() {
  const [state, setState] = useState<DashboardState>({ data: null, loading: true, error: null });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await api.dashboardStats();
      setState({ data, loading: false, error: null });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Couldn't load dashboard stats.";
      setState({ data: null, loading: false, error: message });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}
