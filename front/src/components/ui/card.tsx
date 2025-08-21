import * as React from 'react'
import { cn } from '../../lib/utils'

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-xl border border-gray-200 bg-white text-gray-900 shadow-sm',
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-6', className)}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('font-semibold leading-none tracking-tight', className)}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-gray-600', className)} {...props} />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center p-6 pt-0', className)}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

const MemoizedCard = React.memo(Card)
const MemoizedCardHeader = React.memo(CardHeader)
const MemoizedCardTitle = React.memo(CardTitle)
const MemoizedCardDescription = React.memo(CardDescription)
const MemoizedCardContent = React.memo(CardContent)
const MemoizedCardFooter = React.memo(CardFooter)

MemoizedCard.displayName = 'Card'
MemoizedCardHeader.displayName = 'CardHeader'
MemoizedCardTitle.displayName = 'CardTitle'
MemoizedCardDescription.displayName = 'CardDescription'
MemoizedCardContent.displayName = 'CardContent'
MemoizedCardFooter.displayName = 'CardFooter'

export { 
  MemoizedCard as Card, 
  MemoizedCardHeader as CardHeader, 
  MemoizedCardFooter as CardFooter, 
  MemoizedCardTitle as CardTitle, 
  MemoizedCardDescription as CardDescription, 
  MemoizedCardContent as CardContent 
}
