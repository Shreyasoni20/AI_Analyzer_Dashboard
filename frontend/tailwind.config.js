/** @type {import('tailwindcss').Config} */

module.exports = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],

  theme: {
    extend: {

      colors: {

        primary: "var(--color-primary)",
        "primary-foreground": "var(--color-primary-foreground)",

        secondary: "var(--color-secondary)",
        "secondary-foreground": "var(--color-secondary-foreground)",

        background: "var(--color-background)",
        foreground: "var(--color-foreground)",

        card: "var(--color-card)",
        "card-foreground": "var(--color-card-foreground)",

        muted: "var(--color-muted)",
        "muted-foreground": "var(--color-muted-foreground)",

        border: "var(--color-border)",
        ring: "var(--color-ring)",

        success: "var(--color-success)",
        warning: "var(--color-warning)",
        error: "var(--color-error)"

      },

      borderRadius: {
        xl: "12px"
      }

    }
  },

  plugins: []
}