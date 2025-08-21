/**
 * Storage utilities for handling IndexedDB and localStorage errors
 */

export const clearCorruptedStorage = () => {
  try {
    // Clear localStorage items that might be corrupted
    const keysToCheck = ['auth-storage', 'ui-preferences']
    
    keysToCheck.forEach(key => {
      try {
        const item = localStorage.getItem(key)
        if (item) {
          JSON.parse(item) // Test if it's valid JSON
        }
      } catch (error) {
        console.warn(`Clearing corrupted localStorage item: ${key}`)
        localStorage.removeItem(key)
      }
    })
    
    // Clear IndexedDB if possible
    if (typeof window !== 'undefined' && 'indexedDB' in window) {
      // Clear Zustand persist stores
      clearIndexedDBStores(['auth-storage', 'ui-preferences'])
    }
  } catch (error) {
    console.warn('Error clearing storage:', error)
  }
}

const clearIndexedDBStores = (storeNames: string[]) => {
  storeNames.forEach(storeName => {
    try {
      const deleteReq = indexedDB.deleteDatabase(storeName)
      deleteReq.onerror = () => {
        console.warn(`Failed to delete IndexedDB: ${storeName}`)
      }
      deleteReq.onsuccess = () => {
        console.log(`Cleared IndexedDB: ${storeName}`)
      }
    } catch (error) {
      console.warn(`Error deleting IndexedDB ${storeName}:`, error)
    }
  })
}

export const handleStorageError = (error: any, storeName: string) => {
  console.error(`Storage error in ${storeName}:`, error)
  
  // If it's an IndexedDB error, try to clear and reload
  if (error.name === 'NotFoundError' && error.message.includes('object stores')) {
    console.warn(`IndexedDB schema error in ${storeName}, clearing storage`)
    clearCorruptedStorage()
    // Optionally reload the page to start fresh
    if (confirm('Storage error detected. Reload page to fix?')) {
      window.location.reload()
    }
  }
}

// Initialize storage error handling
export const initStorageErrorHandling = () => {
  // Handle unhandled IndexedDB errors
  if (typeof window !== 'undefined') {
    window.addEventListener('error', (event) => {
      if (event.error && event.error.name === 'NotFoundError') {
        handleStorageError(event.error, 'global')
      }
    })
    
    window.addEventListener('unhandledrejection', (event) => {
      if (event.reason && event.reason.name === 'NotFoundError') {
        handleStorageError(event.reason, 'global')
        event.preventDefault() // Prevent console error
      }
    })
  }
}