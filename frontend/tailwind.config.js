/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef9ff',
          100: '#d8f1ff',
          200: '#bae7ff',
          300: '#8bd9ff',
          400: '#54c2ff',
          500: '#2da3ff',
          600: '#1685f7',
          700: '#0f6de3',
          800: '#1358b8',
          900: '#164b91',
          950: '#122f58',
        },
        surface: {
          DEFAULT: '#0f1117',
          card: '#161923',
          hover: '#1e2230',
          border: '#2a2e3d',
        },
        long: '#22c55e',
        short: '#ef4444',
      },
    },
  },
  plugins: [],
};
