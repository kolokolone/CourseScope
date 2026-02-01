'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

type XAxis = 'time' | 'distance';

type UiPrefsState = {
  chartsXAxis: XAxis;
  setChartsXAxis: (axis: XAxis) => void;

  chartsSmoothWindow: number;
  setChartsSmoothWindow: (value: number) => void;

  mapColorByPace: boolean;
  setMapColorByPace: (value: boolean) => void;

  mapPausePoints: boolean;
  setMapPausePoints: (value: boolean) => void;
};

export const useUiPrefsStore = create<UiPrefsState>()(
  persist(
    (set) => ({
      chartsXAxis: 'time',
      setChartsXAxis: (axis) => set({ chartsXAxis: axis }),

      chartsSmoothWindow: 10,
      setChartsSmoothWindow: (value) => set({ chartsSmoothWindow: value }),

      mapColorByPace: false,
      setMapColorByPace: (value) => set({ mapColorByPace: value }),

      mapPausePoints: false,
      setMapPausePoints: (value) => set({ mapPausePoints: value }),
    }),
    {
      name: 'coursescope-ui-prefs',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
