/**
 * Virtual Scrolling Hook for Performance Optimization
 * Handles large lists efficiently by only rendering visible items
 */

import { useState, useEffect, useMemo, useCallback } from 'react'

interface UseVirtualizationProps {
  itemCount: number
  itemHeight: number
  containerHeight: number
  overscan?: number
}

interface VirtualItem {
  index: number
  start: number
  end: number
}

export const useVirtualization = ({
  itemCount,
  itemHeight,
  containerHeight,
  overscan = 5
}: UseVirtualizationProps) => {
  const [scrollTop, setScrollTop] = useState(0)

  const visibleRange = useMemo(() => {
    const startIndex = Math.floor(scrollTop / itemHeight)
    const endIndex = Math.min(
      itemCount - 1,
      Math.floor((scrollTop + containerHeight) / itemHeight)
    )

    return {
      start: Math.max(0, startIndex - overscan),
      end: Math.min(itemCount - 1, endIndex + overscan)
    }
  }, [scrollTop, itemHeight, containerHeight, itemCount, overscan])

  const virtualItems = useMemo((): VirtualItem[] => {
    const items: VirtualItem[] = []
    
    for (let i = visibleRange.start; i <= visibleRange.end; i++) {
      items.push({
        index: i,
        start: i * itemHeight,
        end: (i + 1) * itemHeight
      })
    }

    return items
  }, [visibleRange, itemHeight])

  const totalHeight = itemCount * itemHeight

  const handleScroll = useCallback((event: React.UIEvent<HTMLElement>) => {
    setScrollTop(event.currentTarget.scrollTop)
  }, [])

  return {
    virtualItems,
    totalHeight,
    scrollTop,
    handleScroll,
    visibleRange
  }
}