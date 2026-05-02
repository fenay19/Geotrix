import { create } from "zustand";

interface User {
  id: number;
  email: string;
  is_admin: boolean;
}

interface UIState {
  theme: "dark" | "light";
  activeTab: string;
  selectedAssetSymbol: string | null;
  selectedCountryId: number | null;
  activeModal: string | null;
  modalData: any;
  activeChatSessionId: number | null;
  filters: {
    eventSearch: string;
    eventSeverity: number;
    marketCategory: string;
    signalAssetClass: string;
    signalDirection: string;
    supplyChainNodeType: string;
    supplyChainLocation: string;
  };
  user: User | null;
  token: string | null;

  setTheme: (theme: "dark" | "light") => void;
  setActiveTab: (tab: string) => void;
  setSelectedAssetSymbol: (symbol: string | null) => void;
  setSelectedCountryId: (id: number | null) => void;
  setActiveModal: (modal: string | null, data?: any) => void;
  setActiveChatSessionId: (id: number | null) => void;
  setFilters: (update: Partial<UIState["filters"]>) => void;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  theme: "dark",
  activeTab: "dashboard",
  selectedAssetSymbol: null,
  selectedCountryId: null,
  activeModal: null,
  modalData: null,
  activeChatSessionId: null,
  filters: {
    eventSearch: "",
    eventSeverity: 1,
    marketCategory: "all",
    signalAssetClass: "all",
    signalDirection: "all",
    supplyChainNodeType: "all",
    supplyChainLocation: "all",
  },
  user: null,
  token: localStorage.getItem("geotrade_token"),

  setTheme: (theme) => set({ theme }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedAssetSymbol: (selectedAssetSymbol) => set({ selectedAssetSymbol }),
  setSelectedCountryId: (selectedCountryId) => set({ selectedCountryId }),
  setActiveModal: (activeModal, modalData = null) => set({ activeModal, modalData }),
  setActiveChatSessionId: (activeChatSessionId) => set({ activeChatSessionId }),
  setFilters: (update) =>
    set((state) => ({ filters: { ...state.filters, ...update } })),
  setUser: (user) => set({ user }),
  setToken: (token) => {
    if (token) {
      localStorage.setItem("geotrade_token", token);
    } else {
      localStorage.removeItem("geotrade_token");
    }
    set({ token });
  },
  logout: () => {
    localStorage.removeItem("geotrade_token");
    set({ user: null, token: null, activeTab: "dashboard" });
  },
}));
