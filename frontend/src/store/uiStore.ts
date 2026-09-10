import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type UiStore = {
  selectedAoiId: string | null;
  showAlerts: boolean;
  showLossOverlay: boolean;
  showNdvi: boolean;
  showForestMask: boolean;
  overlayOpacity: number;
  focusAlertId: string | null;
  setSelectedAoiId: (id: string | null) => void;
  setLayer: (name: 'showAlerts' | 'showLossOverlay' | 'showNdvi' | 'showForestMask', value: boolean) => void;
  setOverlayOpacity: (value: number) => void;
  setFocusAlertId: (id: string | null) => void;
};

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      selectedAoiId: null,
      showAlerts: true,
      showLossOverlay: true,
      showNdvi: false,
      showForestMask: true,
      overlayOpacity: 70,
      focusAlertId: null,
      setSelectedAoiId: (id) => set({ selectedAoiId: id }),
      setLayer: (name, value) => set({ [name]: value }),
      setOverlayOpacity: (value) => set({ overlayOpacity: value }),
      setFocusAlertId: (id) => set({ focusAlertId: id }),
    }),
    {
      name: 'dw_ui',
      partialize: (state) => ({
        showLossOverlay: state.showLossOverlay,
        overlayOpacity: state.overlayOpacity,
      }),
    },
  ),
);
