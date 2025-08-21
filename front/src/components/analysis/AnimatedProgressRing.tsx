import React from 'react'
import { motion } from 'framer-motion'

interface AnimatedProgressRingProps {
  progress: number
  isPaused?: boolean
  size?: number
  strokeWidth?: number
  className?: string
}

export const AnimatedProgressRing: React.FC<AnimatedProgressRingProps> = ({
  progress,
  isPaused = false,
  size = 120,
  strokeWidth = 8,
  className = ''
}) => {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (progress / 100) * circumference

  // Calculate colors based on progress and state
  const getColors = () => {
    if (isPaused) {
      return {
        background: 'rgb(251 191 36 / 0.2)', // amber-400 with opacity
        progress: 'rgb(245 158 11)', // amber-500
        glow: 'rgb(245 158 11 / 0.3)'
      }
    }

    if (progress < 25) {
      return {
        background: 'rgb(59 130 246 / 0.2)', // blue-500 with opacity
        progress: 'rgb(59 130 246)', // blue-500
        glow: 'rgb(59 130 246 / 0.3)'
      }
    } else if (progress < 50) {
      return {
        background: 'rgb(168 85 247 / 0.2)', // purple-500 with opacity
        progress: 'rgb(168 85 247)', // purple-500
        glow: 'rgb(168 85 247 / 0.3)'
      }
    } else if (progress < 75) {
      return {
        background: 'rgb(236 72 153 / 0.2)', // pink-500 with opacity
        progress: 'rgb(236 72 153)', // pink-500
        glow: 'rgb(236 72 153 / 0.3)'
      }
    } else {
      return {
        background: 'rgb(34 197 94 / 0.2)', // green-500 with opacity
        progress: 'rgb(34 197 94)', // green-500
        glow: 'rgb(34 197 94 / 0.3)'
      }
    }
  }

  const colors = getColors()

  return (
    <div
      className={`relative ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        style={{ filter: 'drop-shadow(0 0 8px rgba(0, 0, 0, 0.1))' }}
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.background}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeLinecap="round"
        />

        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.progress}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          initial={{ strokeDashoffset: circumference }}
          animate={{
            strokeDashoffset,
            filter: isPaused ? 'none' : `drop-shadow(0 0 6px ${colors.glow})`
          }}
          transition={{
            strokeDashoffset: {
              duration: 1.5,
              ease: [0.4, 0.0, 0.2, 1] // Custom cubic bezier for smooth animation
            },
            filter: {
              duration: 0.3
            }
          }}
          style={{
            filter: isPaused ? 'none' : `drop-shadow(0 0 6px ${colors.glow})`
          }}
        />

        {/* Animated glow effect for active state */}
        {!isPaused && progress > 0 && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={colors.progress}
            strokeWidth={strokeWidth + 2}
            fill="transparent"
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            opacity={0.4}
            animate={{
              opacity: [0.2, 0.6, 0.2],
              strokeWidth: [strokeWidth + 1, strokeWidth + 4, strokeWidth + 1]
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut'
            }}
          />
        )}

        {/* Progress indicator dot */}
        {progress > 0 && (
          <motion.circle
            cx={
              size / 2 +
              radius * Math.cos(-Math.PI / 2 + (progress / 100) * 2 * Math.PI)
            }
            cy={
              size / 2 +
              radius * Math.sin(-Math.PI / 2 + (progress / 100) * 2 * Math.PI)
            }
            r={strokeWidth / 2 + 2}
            fill={colors.progress}
            initial={{ scale: 0 }}
            animate={{
              scale: 1,
              boxShadow: isPaused ? 'none' : `0 0 12px ${colors.glow}`
            }}
            transition={{
              scale: { delay: 0.5, duration: 0.3 },
              boxShadow: { duration: 0.3 }
            }}
          />
        )}
      </svg>

      {/* Pulse animation for active state */}
      {!isPaused && progress > 0 && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle, ${colors.glow} 0%, transparent 70%)`
          }}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.1, 0.3]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
        />
      )}

      {/* Completion celebration effect */}
      {progress >= 100 && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ scale: 0 }}
          animate={{
            scale: [0, 1.5, 1],
            rotate: [0, 360]
          }}
          transition={{
            scale: { duration: 0.6, times: [0, 0.6, 1] },
            rotate: { duration: 0.8 }
          }}
        >
          <div
            className="w-full h-full rounded-full border-4"
            style={{
              borderColor: colors.progress,
              boxShadow: `0 0 20px ${colors.glow}, inset 0 0 20px ${colors.glow}`
            }}
          />
        </motion.div>
      )}
    </div>
  )
}
