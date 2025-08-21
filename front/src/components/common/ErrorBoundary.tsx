/**
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the component tree
 */

import React from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<ErrorFallbackProps>
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorFallbackProps {
  error: Error
  resetError: () => void
  errorInfo?: React.ErrorInfo
}

const DefaultErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetError,
  errorInfo
}) => {
  const isDevelopment = import.meta.env.DEV

  const handleReload = () => {
    window.location.reload()
  }

  const handleGoHome = () => {
    window.location.href = '/'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 p-3 bg-red-100 rounded-full w-fit">
            <AlertTriangle className="size-8 text-red-600" />
          </div>
          <CardTitle className="text-xl text-gray-900">
            Something went wrong
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-600 text-center">
            We encountered an unexpected error. This has been logged and our team will investigate.
          </p>
          
          {isDevelopment && (
            <div className="space-y-3">
              <details className="text-sm">
                <summary className="cursor-pointer text-red-600 font-medium">
                  Error Details (Development)
                </summary>
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                  <p className="font-medium text-red-800 mb-1">Error:</p>
                  <pre className="text-xs text-red-700 whitespace-pre-wrap break-words">
                    {error.message}
                  </pre>
                  
                  {error.stack && (
                    <>
                      <p className="font-medium text-red-800 mt-3 mb-1">Stack Trace:</p>
                      <pre className="text-xs text-red-700 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                        {error.stack}
                      </pre>
                    </>
                  )}
                  
                  {errorInfo?.componentStack && (
                    <>
                      <p className="font-medium text-red-800 mt-3 mb-1">Component Stack:</p>
                      <pre className="text-xs text-red-700 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                        {errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              </details>
            </div>
          )}
          
          <div className="flex flex-col sm:flex-row gap-2 pt-4">
            <Button onClick={resetError} className="flex-1">
              <RefreshCw className="size-4 mr-2" />
              Try Again
            </Button>
            <Button variant="outline" onClick={handleReload} className="flex-1">
              Reload Page
            </Button>
            <Button variant="outline" onClick={handleGoHome} className="flex-1">
              <Home className="size-4 mr-2" />
              Go Home
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    this.setState({
      error,
      errorInfo
    })
    
    // Call optional error handler
    this.props.onError?.(error, errorInfo)
    
    // Log to error reporting service in production
    if (import.meta.env.PROD) {
      // Example: Sentry.captureException(error, { contexts: { errorInfo } })
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      const ErrorFallbackComponent = this.props.fallback || DefaultErrorFallback
      
      return (
        <ErrorFallbackComponent
          error={this.state.error!}
          resetError={this.handleReset}
          errorInfo={this.state.errorInfo}
        />
      )
    }

    return this.props.children
  }
}

/**
 * HOC for wrapping components with error boundary
 */
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  )
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`
  
  return WrappedComponent
}