import { useCallback, useEffect, useState } from "react"

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === "undefined") return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item ? (JSON.parse(item) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const valueToStore = value instanceof Function ? value(prev) : value
        try {
          window.localStorage.setItem(key, JSON.stringify(valueToStore))
        } catch {
          // quota exceeded or private browsing — fail silently
        }
        return valueToStore
      })
    },
    [key],
  )

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== key || event.newValue == null) return
      try {
        setStoredValue(JSON.parse(event.newValue) as T)
      } catch {
        // ignore parse errors from other tabs
      }
    }
    window.addEventListener("storage", onStorage)
    return () => window.removeEventListener("storage", onStorage)
  }, [key])

  return [storedValue, setValue] as const
}
