import { create } from "zustand"

/**
 * Single source of truth for the user's default display currency.
 *
 * Initialized from the server preferences on app startup (via AppSidebar's
 * `usePreferences` fetch), and updated whenever the user changes it in Settings.
 *
 * Per-page currency selectors should use `defaultDisplayCurrency` as their initial
 * state, while still allowing the user to temporarily override it for that session.
 *
 * Note: Home currency (used for FX exposure calculations) is stored on the active
 * investment profile (`UserInvestmentProfile.home_currency`) and is managed via
 * the profile API — not here.
 */
interface DefaultCurrencyState {
  defaultDisplayCurrency: string
  setDefaultDisplayCurrency: (currency: string) => void
  initialize: (defaultDisplayCurrency: string) => void
}

export const useDefaultCurrency = create<DefaultCurrencyState>((set) => ({
  defaultDisplayCurrency: "USD",
  setDefaultDisplayCurrency: (currency) => set({ defaultDisplayCurrency: currency }),
  initialize: (defaultDisplayCurrency) => set({ defaultDisplayCurrency }),
}))
