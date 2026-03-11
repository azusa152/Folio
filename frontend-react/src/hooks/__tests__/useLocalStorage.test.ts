import { describe, it, expect, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useLocalStorage } from "../useLocalStorage"

beforeEach(() => {
  window.localStorage.clear()
})

describe("useLocalStorage", () => {
  it("returns initial value when localStorage is empty", () => {
    const { result } = renderHook(() => useLocalStorage("test-key", false))
    expect(result.current[0]).toBe(false)
  })

  it("reads existing value from localStorage", () => {
    window.localStorage.setItem("test-key", JSON.stringify(true))
    const { result } = renderHook(() => useLocalStorage("test-key", false))
    expect(result.current[0]).toBe(true)
  })

  it("writes to localStorage when setValue is called", () => {
    const { result } = renderHook(() => useLocalStorage("test-key", "hello"))
    act(() => {
      result.current[1]("world")
    })
    expect(result.current[0]).toBe("world")
    expect(JSON.parse(window.localStorage.getItem("test-key")!)).toBe("world")
  })

  it("supports functional updater", () => {
    const { result } = renderHook(() => useLocalStorage("counter", 0))
    act(() => {
      result.current[1]((prev) => prev + 1)
    })
    expect(result.current[0]).toBe(1)
    expect(JSON.parse(window.localStorage.getItem("counter")!)).toBe(1)
  })

  it("falls back to initial value on corrupt JSON", () => {
    window.localStorage.setItem("test-key", "not-json")
    const { result } = renderHook(() => useLocalStorage("test-key", 42))
    expect(result.current[0]).toBe(42)
  })

  it("works with object values", () => {
    const initial = { expanded: false, count: 0 }
    const { result } = renderHook(() => useLocalStorage("obj-key", initial))
    act(() => {
      result.current[1]({ expanded: true, count: 5 })
    })
    expect(result.current[0]).toEqual({ expanded: true, count: 5 })
  })
})
