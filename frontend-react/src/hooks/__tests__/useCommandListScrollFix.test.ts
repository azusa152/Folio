import { describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"
import { type TouchEvent, type WheelEvent } from "react"
import { useCommandListScrollFix } from "../useCommandListScrollFix"

function createTouchEvent(y: number) {
  return {
    changedTouches: [{ clientY: y }],
    stopPropagation: vi.fn(),
  }
}

describe("useCommandListScrollFix", () => {
  it("maps mouse wheel down/up to ArrowDown/ArrowUp events", () => {
    const { result } = renderHook(() => useCommandListScrollFix())
    const target = document.createElement("div")
    const keydownSpy = vi.fn()
    target.addEventListener("keydown", keydownSpy)

    const downEvent = { currentTarget: target, deltaY: 42, stopPropagation: vi.fn() }
    const upEvent = { currentTarget: target, deltaY: -10, stopPropagation: vi.fn() }

    act(() => {
      result.current.onWheel(downEvent as unknown as WheelEvent<HTMLElement>)
      result.current.onWheel(upEvent as unknown as WheelEvent<HTMLElement>)
    })

    expect(downEvent.stopPropagation).toHaveBeenCalled()
    expect(upEvent.stopPropagation).toHaveBeenCalled()
    expect(keydownSpy).toHaveBeenCalledTimes(2)
    expect((keydownSpy.mock.calls[0]?.[0] as KeyboardEvent).key).toBe("ArrowDown")
    expect((keydownSpy.mock.calls[1]?.[0] as KeyboardEvent).key).toBe("ArrowUp")
  })

  it("maps touch move direction to ArrowDown/ArrowUp events", () => {
    const { result } = renderHook(() => useCommandListScrollFix())
    const target = document.createElement("div")
    const keydownSpy = vi.fn()
    target.addEventListener("keydown", keydownSpy)

    const touchStart = createTouchEvent(300)
    const touchMoveDown = createTouchEvent(240)
    const touchMoveUp = createTouchEvent(320)

    act(() => {
      result.current.onTouchStart(touchStart as unknown as TouchEvent<HTMLElement>)
      result.current.onTouchMove({ ...touchMoveDown, currentTarget: target } as unknown as TouchEvent<HTMLElement>)
      result.current.onTouchMove({ ...touchMoveUp, currentTarget: target } as unknown as TouchEvent<HTMLElement>)
    })

    expect(touchMoveDown.stopPropagation).toHaveBeenCalled()
    expect(touchMoveUp.stopPropagation).toHaveBeenCalled()
    expect(keydownSpy).toHaveBeenCalledTimes(2)
    expect((keydownSpy.mock.calls[0]?.[0] as KeyboardEvent).key).toBe("ArrowDown")
    expect((keydownSpy.mock.calls[1]?.[0] as KeyboardEvent).key).toBe("ArrowUp")
  })
})
