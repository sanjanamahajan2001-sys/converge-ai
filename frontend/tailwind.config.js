/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          base: "#FAF7F2",       // Warm Alabaster Paper
          surface: "#FFFFFF",    // Pure Card Surface
          elevated: "#F5EFE8",   // Subtle Inset / Control Wells
          sunken: "#EDE6DC",     // Sunken Backgrounds
          border: "#E5DED3",     // Hairline Editorial Border
          "border-strong": "#CEBFAD",
        },
        ink: {
          primary: "#1C1917",    // Deep Stone Charcoal
          secondary: "#57534E",  // Editorial Muted
          muted: "#857D74",      // Timestamps & Meta
        },
        brass: {
          DEFAULT: "#B47834",    // Burnished Brass Accent
          hover: "#966127",
          light: "#F7EFE4",
        },
        terracotta: {
          DEFAULT: "#C25438",    // Kiln Fire Accent
          hover: "#A4422A",
          light: "#FAEEEA",
        },
        sage: {
          DEFAULT: "#3E634F",    // Forest Sage Accent
          hover: "#2E4C3C",
          light: "#EDF3EF",
        },
        status: {
          success: "#2E5A44",
          warning: "#9E6B15",
          danger: "#992E2E",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          "Oxygen-Sans",
          "Ubuntu",
          "Cantarell",
          '"Helvetica Neue"',
          "sans-serif",
        ],
        serif: [
          "Charter",
          '"Bitstream Charter"',
          '"Sitka Text"',
          "Cambria",
          "Georgia",
          '"Times New Roman"',
          "serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          '"Liberation Mono"',
          '"Courier New"',
          "monospace",
        ],
      },
    },
  },
  plugins: [],
}
