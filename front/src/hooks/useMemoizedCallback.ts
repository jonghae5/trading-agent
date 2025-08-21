/**
 * Memoization Hooks for Performance Optimization
 * Prevents unnecessary re-renders and calculations
 */

import { useCallback, useRef, useMemo, useState, useEffect } from 'react'

/**
 * Deep comparison for objects and arrays
 */
function deepEqual(a: any, b: any): boolean {
  if (a === b) return true
  
  if (a == null || b == null) return false
  
  if (typeof a !== typeof b) return false
  
  if (typeof a !== 'object') return false
  
  if (Array.isArray(a) !== Array.isArray(b)) return false
  
  if (Array.isArray(a)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false
    }
    return true
  }
  
  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  
  if (keysA.length !== keysB.length) return false
  
  for (let key of keysA) {
    if (!keysB.includes(key)) return false
    if (!deepEqual(a[key], b[key])) return false
  }
  
  return true
}

/**
 * useMemoizedCallback - Memoizes callback with deep comparison
 */
export const useMemoizedCallback = <T extends (...args: any[]) => any>(
  callback: T,
  deps: any[]
): T => {
  const ref = useRef<{ deps: any[]; callback: T }>()
  
  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    ref.current = { deps, callback }
  }
  
  return ref.current.callback
}

/**
 * useDeepMemo - Memoizes value with deep comparison
 */
export const useDeepMemo = <T>(factory: () => T, deps: any[]): T => {
  const ref = useRef<{ deps: any[]; value: T }>()
  
  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    ref.current = { deps, value: factory() }
  }
  
  return ref.current.value
}

/**
 * useStableCallback - Creates a stable callback reference
 */
export const useStableCallback = <T extends (...args: any[]) => any>(
  callback: T
): T => {
  const callbackRef = useRef(callback)
  callbackRef.current = callback
  
  return useCallback(
    ((...args: any[]) => callbackRef.current(...args)) as T,
    []
  )
}

/**
 * useMemoizedValue - Memoizes expensive calculations
 */
export const useMemoizedValue = <T>(
  factory: () => T,
  deps: any[],
  deepComparison = false
): T => {
  if (deepComparison) {
    return useDeepMemo(factory, deps)
  }
  
  return useMemo(factory, deps)
}

/**
 * useThrottledCallback - Throttles callback execution
 */
export const useThrottledCallback = <T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T => {
  const lastCall = useRef<number>(0)
  const timeoutRef = useRef<NodeJS.Timeout>()
  
  return useCallback(
    ((...args: any[]) => {
      const now = Date.now()
      
      if (now - lastCall.current >= delay) {
        lastCall.current = now
        callback(...args)
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
        }
        
        timeoutRef.current = setTimeout(() => {
          lastCall.current = Date.now()
          callback(...args)
        }, delay - (now - lastCall.current))
      }
    }) as T,
    [callback, delay]
  )
}

/**
 * useDebounce - Debounces value changes
 */
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value)
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)
    
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])
  
  return debouncedValue
}