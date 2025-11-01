/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../**/templates/**/*.html',
    '../../**/components/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // ============================================
        // KEEPA IA - PALETA DE COLORES
        // ============================================
        // Para cambiar la paleta, modifica estos valores y recompila Tailwind
        // Comando: cd theme/static_src && npm run build
        // ============================================
        
        // Keepa Blue - Color principal de la marca
        // Usado para: botones principales, enlaces, acentos
        'keepa-blue': {
          50: '#f0f9ff',   // Fondo muy claro
          100: '#e0f2fe',  // Fondo claro
          200: '#bae6fd',  // Fondo suave
          300: '#7dd3fc',  // Elementos secundarios
          400: '#38bdf8',  // Hover states
          500: '#0ea5e9',  // Base
          600: '#0284c7',  // Botones principales ⭐
          700: '#0369a1',  // Botones hover ⭐
          800: '#075985',  // Texto sobre fondo claro
          900: '#0c4a6e',  // Texto destacado
          950: '#082f49',  // Texto muy oscuro
        },
        
        // Keepa Green - Color de éxito/confirmación
        // Usado para: acciones exitosas, confirmaciones, badges de éxito
        'keepa-green': {
          50: '#ecfdf5',   // Fondo muy claro
          100: '#d1fae5',  // Fondo claro
          200: '#a7f3d0',  // Fondo suave
          300: '#6ee7b7',  // Elementos secundarios
          400: '#34d399',  // Hover states
          500: '#10b981',  // Base
          600: '#059669',  // Botones de éxito ⭐
          700: '#047857',  // Hover ⭐
          800: '#065f46',  // Texto sobre fondo claro
          900: '#064e3b',  // Texto destacado
          950: '#022c22',  // Texto muy oscuro
        },
        
        // Keepa Orange - Color de advertencia/destacado
        // Usado para: alertas, elementos destacados, llamadas a la acción
        'keepa-orange': {
          50: '#fff7ed',   // Fondo muy claro
          100: '#ffedd5',  // Fondo claro
          200: '#fed7aa',  // Fondo suave
          300: '#fdba74',  // Elementos secundarios
          400: '#fb923c',  // Hover states
          500: '#f97316',  // Base
          600: '#ea580c',  // Botones de advertencia ⭐
          700: '#c2410c',  // Hover ⭐
          800: '#9a3412',  // Texto sobre fondo claro
          900: '#7c2d12',  // Texto destacado
          950: '#431407',  // Texto muy oscuro
        },
        
        // Fondo oscuro para Glassmorphism
        // Gradiente base: from-slate-900 via-indigo-950 to-slate-900
        // Para cambiar el fondo, modifica el body en styles.css
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        // Animaciones básicas
        'fade-in': 'fadeIn 0.6s ease-out',
        'fade-in-slow': 'fadeIn 0.8s ease-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'slide-down': 'slideDown 0.4s ease-out',
        'slide-in-left': 'slideInLeft 0.6s ease-out',
        'slide-in-right': 'slideInRight 0.6s ease-out',
        'scale-in': 'scaleIn 0.5s ease-out',
        'bounce-in': 'bounceIn 0.8s ease-out',
        
        // Animaciones con delays para stagger effect
        'fade-in-delay-100': 'fadeIn 0.6s ease-out 0.1s both',
        'fade-in-delay-200': 'fadeIn 0.6s ease-out 0.2s both',
        'fade-in-delay-300': 'fadeIn 0.6s ease-out 0.3s both',
        'fade-in-delay-400': 'fadeIn 0.6s ease-out 0.4s both',
        'fade-in-delay-500': 'fadeIn 0.6s ease-out 0.5s both',
        
        'slide-up-delay-100': 'slideUp 0.6s ease-out 0.1s both',
        'slide-up-delay-200': 'slideUp 0.6s ease-out 0.2s both',
        'slide-up-delay-300': 'slideUp 0.6s ease-out 0.3s both',
        'slide-up-delay-400': 'slideUp 0.6s ease-out 0.4s both',
        'slide-up-delay-500': 'slideUp 0.6s ease-out 0.5s both',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-30px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(30px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        bounceIn: {
          '0%': { transform: 'scale(0.3)', opacity: '0' },
          '50%': { transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
  safelist: [
    'alert-error',
    'alert-success',
    'alert-warning',
    'alert-info',
    {
      pattern: /alert-(error|success|warning|info)/,
    },
  ],
}

