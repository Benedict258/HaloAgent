/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    DEFAULT: '#C85A47',
                    50: '#F9E8E5',
                    100: '#F3D1CB',
                    200: '#E8A398',
                    300: '#DC7565',
                    400: '#D16856',
                    500: '#C85A47',
                    600: '#A04839',
                    700: '#78362B',
                    800: '#50241D',
                    900: '#28120E',
                },
            },
        },
    },
    plugins: [],
}
