/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  darkMode: ['class'], // Enable dark mode support
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
      // Updated color palette for better aesthetics
      colors: {
        // Primary colors (green tones)
        primary: '#2A6041', // Main green
        'primary-500': '#2A6041', // Main green
        'primary-600': '#1F4A32', // Darker green for hover
        'primary-400': '#3A7A56', // Lighter green for borders/backgrounds
        'primary-300': '#4BAF7E', // Light green for accents
        'primary-200': '#A3E2B0', // Very light green for backgrounds
        // Secondary colors (yellow tones)
        secondary: '#FFC857', // Main yellow
        'secondary-500': '#FFC857', // Bright yellow for accents
        'secondary-600': '#E6B347', // Darker yellow for hover
        'secondary-400': '#FFD580', // Lighter yellow for backgrounds

        // Neutral colors (gray tones)
        'off-white': '#F5F5F5', // Soft white for backgrounds
        'dark-1': '#F9FAFB', // Light gray for cards
        'dark-2': '#E5E7EB', // Gray for borders
        'dark-3': '#D1D5DB', // Medium gray for text
        'dark-4': '#9CA3AF', // Dark gray for disabled states

        // Text colors
        'light-1': '#111827', // Dark black for main text
        'light-2': '#374151', // Dark gray for secondary text
        'light-3': '#4B5563', // Medium gray for hints
        'light-4': '#6B7280', // Light gray for placeholders

        // Accent colors (red tones)
        'red': '#EF4444', // Bright red for errors
        'red-600': '#DC2626', // Dark red for hover
        'red-400': '#F87171', // Light red for backgrounds

        // Primary colors
        primary: '#2A6041', // Main green
        'primary-foreground': '#FFFFFF', // Text color for primary buttons

        // Destructive colors
        destructive: '#EF4444', // Bright red for errors
        'destructive-foreground': '#FFFFFF', // Text color for destructive buttons

        // Accent colors
        accent: '#FFC857', // Bright yellow for accents
        'accent-foreground': '#111827', // Text color for accent buttons

        // Input and background colors
        input: '#E5E7EB', // Light gray for input borders
        background: '#F9FAFB', // Light background color
        'ring-offset-background': '#FFFFFF', // Background for focus ring offset
        ring: '#3B82F6', // Blue for focus ring
      },
      screens: {
        'xs': '480px', // Extra small screens
      },
      width: {
        '420': '420px', // Custom width for specific components
        '465': '465px', // Custom width for larger components
      },
      fontFamily: {
        'mono': ['Menlo', 'Monaco'], // Monospace fonts
      },
      keyframes: {
        // Accordion animations
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
        'accordion-down': 'accordion-down 0.2s ease-out', // Smooth dropdown
        'accordion-up': 'accordion-up 0.2s ease-out', // Smooth collapse
      },
    },
  },
  plugins: [require('tailwindcss-animate')], // Add animation plugin
};