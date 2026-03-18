import { useMemo, useRef, type TouchEvent, type WheelEvent } from "react"

type ScrollFixHandlers = {
  onWheel: (event: WheelEvent<HTMLElement>) => void
  onTouchStart: (event: TouchEvent<HTMLElement>) => void
  onTouchMove: (event: TouchEvent<HTMLElement>) => void
}

function dispatchArrowKey(target: EventTarget & HTMLElement, key: "ArrowDown" | "ArrowUp") {
  target.dispatchEvent(
    new KeyboardEvent("keydown", {
      key,
      bubbles: true,
      cancelable: true,
    }),
  )
}

export function useCommandListScrollFix(): ScrollFixHandlers {
  const lastTouchYRef = useRef<number | null>(null)

  return useMemo(
    () => ({
      onWheel: (event: WheelEvent<HTMLElement>) => {
        event.stopPropagation()
        dispatchArrowKey(event.currentTarget, event.deltaY > 0 ? "ArrowDown" : "ArrowUp")
      },
      onTouchStart: (event: TouchEvent<HTMLElement>) => {
        lastTouchYRef.current = event.changedTouches[0]?.clientY ?? null
      },
      onTouchMove: (event: TouchEvent<HTMLElement>) => {
        const nextY = event.changedTouches[0]?.clientY ?? null
        if (lastTouchYRef.current == null || nextY == null) return
        event.stopPropagation()
        const isScrollingDown = nextY < lastTouchYRef.current
        dispatchArrowKey(event.currentTarget, isScrollingDown ? "ArrowDown" : "ArrowUp")
        lastTouchYRef.current = nextY
      },
    }),
    [],
  )
}
