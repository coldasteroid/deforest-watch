import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type UiStore = {
  selectedAoiId: string | null;
  showAlerts: boolean;
  showSatellite: boolean;
  showLossOverlay: boolean;
  showNdvi: boolean;
  showForestMask: boolean;
  showNepalEvent: boolean;
  overlayOpacity: number;
  focusAlertId: string | null;
  setSelectedAoiId: (id: string | null) => void;
  setLayer: (name: 'showAlerts' | 'showSatellite' | 'showLossOverlay' | 'showNdvi' | 'showForestMask' | 'showNepalEvent', value: boolean) => void;
  setOverlayOpacity: (value: number) => void;
  setFocusAlertId: (id: string | null) => void;
};

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      selectedAoiId: null,
      showAlerts: true,
      showSatellite: true,
      showLossOverlay: true,
      showNdvi: false,
      showForestMask: true,
      showNepalEvent: false,
      overlayOpacity: 70,
      focusAlertId: null,
      setSelectedAoiId: (id) => set({ selectedAoiId: id }),
      setLayer: (name, value) => set({ [name]: value }),
      setOverlayOpacity: (value) => set({ overlayOpacity: value }),
      setFocusAlertId: (id) => set({ focusAlertId: id }),
    }),
    {
      name: 'dw_ui_live_demo',
      partialize: (state) => ({
        showLossOverlay: state.showLossOverlay,
        showSatellite: state.showSatellite,
        overlayOpacity: state.overlayOpacity,
      }),
    },
  ),
);
