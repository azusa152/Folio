import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ActionBadge } from "../ActionBadge"

describe("ActionBadge", () => {
  it("renders icon and label for NEW_POSITION", () => {
    render(<ActionBadge action="NEW_POSITION" />)
    expect(screen.getByText(/🟢/)).toBeInTheDocument()
    expect(screen.getByText(/new_position/i)).toBeInTheDocument()
  })

  it("renders icon and label for SOLD_OUT", () => {
    render(<ActionBadge action="SOLD_OUT" />)
    expect(screen.getByText(/🔴/)).toBeInTheDocument()
  })

  it("renders icon and label for INCREASED", () => {
    render(<ActionBadge action="INCREASED" />)
    expect(screen.getByText(/🔵/)).toBeInTheDocument()
  })

  it("renders icon and label for DECREASED", () => {
    render(<ActionBadge action="DECREASED" />)
    expect(screen.getByText(/🟡/)).toBeInTheDocument()
  })

  it("renders fallback icon for unknown action", () => {
    render(<ActionBadge action="UNKNOWN_ACTION" />)
    expect(screen.getByText(/⚪/)).toBeInTheDocument()
  })

  it("uses defaultValue from t() — falls back to action string when key is missing", () => {
    render(<ActionBadge action="CUSTOM_ACTION" />)
    // t() returns defaultValue (the action itself) when no translation exists
    expect(screen.getByText(/CUSTOM_ACTION/)).toBeInTheDocument()
  })
})
