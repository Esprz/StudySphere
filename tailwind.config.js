/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      
      },
    },
    extend: {
      colors: {
        'primary-500': '#204035',
        'primary-600': '#0C382E',
        'secondary-500': '#FFB620',
        'off-white': '#4A7169',
        'red': '#FF5A5A',
        'dark-1': '#FFFFFF',
        'dark-12': '#e4e1d8',
        'dark-2': '#e4e1d8',
        'dark-3': '#d9d5c9',
        'dark-4': '#cac3b2',
        'light-1': '#000000',
        'light-2': '#2f251d',
        'light-3': '#5F4B3B',
        'light-4': '#7e6e62',
      },
      screens: {
        'xs': '480px',
      
      },
      width: {
        '420': '420px',
        '465': '465px',
      },
      fontFamily: {
        'mono': ['Menlo','Monaco'],
        letterSpacing: {
          wider: '0.5em',  // 自定义的字间距
        }

      },
      keyframes: {
        'accordion-down': {
          from: { height: 0 },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: 0 },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};