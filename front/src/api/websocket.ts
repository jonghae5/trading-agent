import { useEffect, useRef, useState } from 'react'

interface WebSocketMessage {
  type: string
  data: any
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private listeners: Map<string, Function[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(url: string) {
    this.url = url
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)
        
        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.emit(message.type, message.data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = () => {
          this.ws = null
          this.handleReconnect()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  send(type: string, data: any) {
    if (this.isConnected()) {
      this.ws?.send(JSON.stringify({ type, data }))
    }
  }

  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)?.push(callback)
  }

  off(event: string, callback?: Function) {
    if (callback) {
      const callbacks = this.listeners.get(event)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
      }
    } else {
      this.listeners.delete(event)
    }
  }

  private emit(event: string, data: any) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => callback(data))
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++
        this.connect().catch(() => {
          // Reconnection failed, will try again or give up
        })
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts))
    }
  }
}

// Create a default WebSocket client instance
export const webSocketClient = new WebSocketClient(
  process.env.NODE_ENV === 'production' 
    ? `wss://${window.location.host}/ws`
    : 'ws://localhost:8000/ws'
)

// React hook for using WebSocket
export const useWebSocket = (url?: string) => {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const clientRef = useRef<WebSocketClient | null>(null)

  useEffect(() => {
    const wsUrl = url || (
      process.env.NODE_ENV === 'production' 
        ? `wss://${window.location.host}/ws`
        : 'ws://localhost:8000/ws'
    )
    
    clientRef.current = new WebSocketClient(wsUrl)
    
    clientRef.current.connect()
      .then(() => {
        setIsConnected(true)
        setError(null)
      })
      .catch((err) => {
        setError(err.message)
        setIsConnected(false)
      })

    return () => {
      clientRef.current?.disconnect()
    }
  }, [url])

  return {
    client: clientRef.current,
    isConnected,
    error
  }
}

export default webSocketClient