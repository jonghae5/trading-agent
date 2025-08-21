/** @type {import('tailwindcss').Config} */

export default {
  content: ['./src/**/*.{mjs,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      boxShadow: {
        soft: '0 2px 8px 0 rgba(0, 0, 0, 0.05)',
        medium: '0 4px 16px 0 rgba(0, 0, 0, 0.08)',
        strong: '0 8px 32px 0 rgba(0, 0, 0, 0.12)'
      }
    }
  },
  plugins: []
}
