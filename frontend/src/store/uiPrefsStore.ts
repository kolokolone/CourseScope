'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

type XAxis = 'time' | 'distance';

type UiPrefsState = {
  chartsXAxis: XAxis;
  setChartsXAxis: (axis: XAxis) => void;

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
