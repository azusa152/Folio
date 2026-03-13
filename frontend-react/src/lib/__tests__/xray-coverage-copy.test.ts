import { readFileSync } from "node:fs"
import path from "node:path"
import { describe, expect, it } from "vitest"

type LocaleDict = {
  allocation?: {
    xray?: {
      coverage?: string
    }
  }
}

function readCoverageCopy(locale: "en" | "ja" | "zh-TW" | "zh-CN"): string {
  const localePath = path.resolve(process.cwd(), "public", "locales", `${locale}.json`)
  const parsed = JSON.parse(readFileSync(localePath, "utf-8")) as LocaleDict
  return parsed.allocation?.xray?.coverage ?? ""
}

describe("xray coverage copy", () => {
  it("uses equity-only wording across all supported locales", () => {
    expect(readCoverageCopy("en")).toBe("Covers {{pct}}% of equity exposure (cash and bonds excluded)")
    expect(readCoverageCopy("ja")).toBe("株式エクスポージャーの {{pct}}% をカバー（現金・債券を除く）")
    expect(readCoverageCopy("zh-TW")).toBe("目前覆蓋股票曝險 {{pct}}%（不含現金與債券）")
    expect(readCoverageCopy("zh-CN")).toBe("当前覆盖股票敞口 {{pct}}%（不含现金与债券）")
  })
})
