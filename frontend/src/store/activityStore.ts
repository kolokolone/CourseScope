import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { ActivityMetadata, SeriesInfo } from '@/types/api';

interface ActivityState {
  currentActivity: {
    id: string | null;
    type: 'real' | 'theoretical' | null;
    metadata: ActivityMetadata | null;
  };
  selectedSeries: SeriesInfo[];
  xAxis: 'time' | 'distance';
  range: { from: number | null; to: number | null };
  downsample: number | null;
  loading: boolean;
  error: string | null;
}

interface ActivityActions {
  loadActivity: (id: string) => void;
  setSelectedSeries: (series: SeriesInfo[]) => void;
  setXAxis: (axis: 'time' | 'distance') => void;
  setRange: (range: { from: number | null; to: number | null }) => void;
  setDownsample: (points: number | null) => void;
  clearActivity: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useActivityStore = create<ActivityState & ActivityActions>()(
  devtools(
    (set) => ({
      currentActivity: { id: null, type: null, metadata: null },
      selectedSeries: [],
      xAxis: 'time',
      range: { from: null, to: null },
      downsample: null,
      loading: false,
      error: null,

      loadActivity: (id) =>
        set((state) => ({
          currentActivity: { ...state.currentActivity, id },
          loading: true,
          error: null,
        })),

      setSelectedSeries: (series) =>
        set({ selectedSeries: series }),

      setXAxis: (axis) => set({ xAxis: axis }),

      setRange: (range) => set({ range }),

      setDownsample: (points) => set({ downsample: points }),

      clearActivity: () =>
        set({
          currentActivity: { id: null, type: null, metadata: null },
          selectedSeries: [],
          xAxis: 'time',
          range: { from: null, to: null },
          downsample: null,
          error: null,
        }),

      setLoading: (loading) => set({ loading }),

      setError: (error) => set({ error }),
    }),
    {
      name: 'activity-store',
    }
  )
);
