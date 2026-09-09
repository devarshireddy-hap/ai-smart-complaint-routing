/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#10131A',
          900: '#171B24',
          800: '#232837',
          700: '#333A4D',
          600: '#4A5268',
          500: '#666F86',
          400: '#8A92A6',
          300: '#B5BBC9',
          200: '#DBDEE6',
          100: '#EEF0F4',
          50: '#F7F8FA',
        },
        campus: {
          700: '#1E4A6D',
          600: '#256189',
          500: '#2E7AAD',
          400: '#5B9BC4',
        },
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(16, 19, 26, 0.06), 0 1px 1px rgba(16, 19, 26, 0.04)',
      },
    },
  },
  plugins: [],
};
