/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pinterest: {
          DEFAULT: '#e60023',
          hover: '#bd081c',
          soft: '#fff0f2',
          border: '#fecdd3',
        },
        canvas: '#f7f7f8',
        card: '#ffffff',
        charcoal: {
          DEFAULT: '#111111',
          muted: '#767676',
          light: '#5f5f5f',
          border: '#ebebeb',
          surface: '#f0f0f2',
        },
        brand: {
          50: '#fff0f2',
          100: '#ffe2e5',
          500: '#e60023',
          600: '#d0021b',
          700: '#bd081c',
        },
        accent: {
          red: '#e60023',
          amber: '#d97706',
          emerald: '#059669',
          blue: '#2563eb',
          slate: '#475569',
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          'ui-monospace',
          'monospace',
        ],
      },
      boxShadow: {
        pin: '0 2px 12px rgba(0, 0, 0, 0.04)',
        'pin-hover': '0 8px 24px rgba(0, 0, 0, 0.08)',
        'pin-modal': '0 20px 40px rgba(0, 0, 0, 0.12)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
