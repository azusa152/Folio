import type { components } from "./generated"

// ---------------------------------------------------------------------------
// Re-exported from dashboard (consumed by allocation hooks/components)
// ---------------------------------------------------------------------------
export type { StockCategory, CategoryAllocation, HoldingDetail, Holding, ProfileResponse } from "./dashboard"

// ---------------------------------------------------------------------------
// Generated from backend Pydantic schemas (single source of truth)
// Do NOT manually edit types that correspond to backend response_model schemas.
// Run `make generate-api` after changing backend/api/schemas.py.
// ---------------------------------------------------------------------------

// Persona templates
export type PersonaTemplate = components["schemas"]["PersonaTemplateResponse"]

// Rebalance (same shape as dashboard RebalanceResponse with xray extension)
export type AllocRebalanceResponse = components["schemas"]["RebalanceResponse"]
export type XRayEntry = components["schemas"]["XRayEntry"]
export type SectorExposureItem = components["schemas"]["SectorExposureItem"]

// Currency exposure
export type CurrencyBreakdown = components["schemas"]["CurrencyBreakdown"]
export type FXMovement = components["schemas"]["FXMovement"]
export type FXRateAlertItem = components["schemas"]["FXRateAlertItem"]
export type CurrencyExposureResponse = components["schemas"]["CurrencyExposureResponse"]

// Stress test
export type StressTestHoldingBreakdown = components["schemas"]["StressTestHoldingBreakdown"]
export type StressTestPainLevel = components["schemas"]["StressTestPainLevel"]
export type StressTestResponse = components["schemas"]["StressTestResponse"]

// Smart withdrawal
export type SellRecommendation = components["schemas"]["SellRecommendationResponse"]
export type WithdrawRequest = components["schemas"]["WithdrawRequest"]
export type WithdrawResponse = components["schemas"]["WithdrawResponse"]

// Telegram & preferences
export type TelegramSettings = components["schemas"]["TelegramSettingsResponse"]
export type AllocPreferencesResponse = components["schemas"]["PreferencesResponse"]

// Request types
export type CreateProfileRequest = components["schemas"]["ProfileCreateRequest"]
export type UpdateProfileRequest = components["schemas"]["ProfileUpdateRequest"]
export type SaveTelegramRequest = components["schemas"]["TelegramSettingsRequest"]
// privacy_mode is required in backend schema; frontend must always include current value
export type SavePreferencesRequest = components["schemas"]["PreferencesRequest"]
