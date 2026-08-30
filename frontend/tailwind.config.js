/** @type {import('tailwindcss').Config} */
export default {
  content: ["./html/*.html", "./ts/**/*.{ts,js}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#07070d", dim: "#0c0d16" },
        surface: { DEFAULT: "#12131f", raised: "#171827" },
        ink: {
          DEFAULT: "#eef6ff",
          soft: "#a9b6c9",
          faint: "#66748a",
        },
        line: "rgba(0, 255, 234, 0.16)",
        "line-strong": "rgba(0, 255, 234, 0.38)",
        accent: {
          DEFAULT: "#ff2ee0",
          deep: "#c400ac",
          soft: "rgba(255, 46, 224, 0.14)",
        },
        teal: {
          DEFAULT: "#00f0ff",
          soft: "rgba(0, 240, 255, 0.12)",
          deep: "#00b8c4",
        },
        danger: {
          DEFAULT: "#ff3860",
          soft: "rgba(255, 56, 96, 0.1)",
          line: "rgba(255, 56, 96, 0.35)",
        },
      },
      fontFamily: {
        display: ["Space Grotesk", "IBM Plex Sans", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "18px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.4), 0 0 24px rgba(0, 240, 255, 0.06)",
        pop: "0 12px 40px rgba(0,0,0,0.6), 0 0 40px rgba(255, 46, 224, 0.12)",
        "glow-accent": "0 0 18px rgba(255, 46, 224, 0.35)",
        "glow-accent-lg": "0 0 26px rgba(255, 46, 224, 0.55)",
        "glow-teal": "0 0 18px rgba(0, 240, 255, 0.3)",
        "glow-word": "0 0 24px rgba(0, 240, 255, 0.25)",
      },
      backgroundImage: {
        "landing-glow":
          "radial-gradient(circle at 20% 15%, rgba(255, 46, 224, 0.10), transparent 45%), radial-gradient(circle at 82% 78%, rgba(0, 240, 255, 0.10), transparent 45%)",
      },
      keyframes: {
        "toast-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "none" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "toast-in": "toast-in .2s ease",
        spin: "spin-slow .7s linear infinite",
      },
    },
  },
  plugins: [],
};
