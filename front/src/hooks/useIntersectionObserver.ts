/**
 * Intersection Observer Hook for Lazy Loading and Performance
 * Optimizes rendering by tracking element visibility
 */

import { useEffect, useRef, useState, useCallback } from 'react'

interface UseIntersectionObserverProps {
  threshold?: number | number[]
  rootMargin?: string
  triggerOnce?: boolean
}

export const useIntersectionObserver = ({
  threshold = 0.1,
  rootMargin = '50px',
  triggerOnce = true
}: UseIntersectionObserverProps = {}) => {
  const [isIntersecting, setIsIntersecting] = useState(false)
  const [hasTriggered, setHasTriggered] = useState(false)
  const elementRef = useRef<HTMLElement>(null)

  const observerCallback = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries
      
      if (entry.isIntersecting) {
        setIsIntersecting(true)
        
        if (triggerOnce) {
          setHasTriggered(true)
        }
      } else if (!triggerOnce) {
        setIsIntersecting(false)
      }
    },
    [triggerOnce]
  )

  useEffect(() => {
    const element = elementRef.current
    
    if (!element || (triggerOnce && hasTriggered)) {
      return
    }

    const observer = new IntersectionObserver(observerCallback, {
      threshold,
      rootMargin
    })

    observer.observe(element)

    return () => {
      observer.unobserve(element)
    }
  }, [observerCallback, threshold, rootMargin, triggerOnce, hasTriggered])

  return {
    elementRef,
    isIntersecting: triggerOnce ? (isIntersecting || hasTriggered) : isIntersecting
  }
}

/**
 * Hook for lazy loading images with intersection observer
 */
export const useLazyImage = (src: string, placeholder?: string) => {
  const [imageSrc, setImageSrc] = useState(placeholder || '')
  const [isLoaded, setIsLoaded] = useState(false)
  const [isError, setIsError] = useState(false)
  
  const { elementRef, isIntersecting } = useIntersectionObserver({
    threshold: 0.1,
    triggerOnce: true
  })

  useEffect(() => {
    if (isIntersecting && src && !isLoaded) {
      const img = new Image()
      
      img.onload = () => {
        setImageSrc(src)
        setIsLoaded(true)
        setIsError(false)
      }
      
      img.onerror = () => {
        setIsError(true)
        setIsLoaded(false)
      }
      
      img.src = src
    }
  }, [isIntersecting, src, isLoaded])

  return {
    elementRef,
    imageSrc,
    isLoaded,
    isError,
    isIntersecting
  }
}