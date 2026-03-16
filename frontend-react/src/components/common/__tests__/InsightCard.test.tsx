import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { InsightCard, type InsightItem } from "../InsightCard"
import { FINANCE_TEXT } from "@/lib/colors"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key}:${JSON.stringify(vars)}` : key,
  }),
}))

describe("InsightCard", () => {
  const insights: InsightItem[] = [
    { key: "insight.a", severity: "info", vars: {}, category: "general" },
    { key: "insight.b", severity: "positive", vars: {}, category: "general" },
    { key: "insight.c", severity: "warning", vars: {}, category: "risk" },
    { key: "insight.d", severity: "action", vars: {}, category: "allocation" },
  ]

  it("renders up to maxVisible by default and can expand", () => {
    render(<InsightCard insights={insights} maxVisible={3} />)

    expect(screen.getByText("insight.a:{}")).toBeInTheDocument()
    expect(screen.getByText("insight.b:{}")).toBeInTheDocument()
    expect(screen.getByText("insight.c:{}")).toBeInTheDocument()
    expect(screen.queryByText("insight.d:{}")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("insight.show_more"))
    expect(screen.getByText("insight.d:{}")).toBeInTheDocument()

    fireEvent.click(screen.getByText("insight.show_less"))
    expect(screen.queryByText("insight.d:{}")).not.toBeInTheDocument()
  })

  it("returns null when no insights", () => {
    const { container } = render(<InsightCard insights={[]} />)
    expect(container.innerHTML).toBe("")
  })

  it("renders loading skeleton when loading and insights are empty", () => {
    const { container } = render(<InsightCard insights={[]} isLoading />)
    expect(screen.getByText("insight.title")).toBeInTheDocument()
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBe(3)
  })

  it("applies severity-specific icon classes", () => {
    render(<InsightCard insights={insights} maxVisible={4} />)

    const infoIcon = screen.getByText("insight.a:{}").previousElementSibling
    const positiveIcon = screen.getByText("insight.b:{}").previousElementSibling
    const warningIcon = screen.getByText("insight.c:{}").previousElementSibling
    const actionIcon = screen.getByText("insight.d:{}").previousElementSibling

    expect(infoIcon).toHaveClass("text-sky-600")
    expect(positiveIcon).toHaveClass(...FINANCE_TEXT.gain.split(" "))
    expect(warningIcon).toHaveClass(...FINANCE_TEXT.warning.split(" "))
    expect(actionIcon).toHaveClass(...FINANCE_TEXT.loss.split(" "))
  })
})
