import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface User {
    id: string
    email: string
    [key: string]: any
}

interface AuthError {
    message: string
}

interface AuthContextType {
    user: User | null
    loading: boolean
    signUp: (email: string, password: string, metadata?: any) => Promise<{ error: AuthError | null }>
    signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>
    signOut: () => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Check for existing token
        const token = localStorage.getItem('auth_token')
        if (token) {
            // Verify token with backend
            fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.user) {
                    setUser(data.user)
                }
            })
            .catch(() => {
                localStorage.removeItem('auth_token')
            })
            .finally(() => setLoading(false))
        } else {
            setLoading(false)
        }
    }, [])

    const signUp = async (email: string, password: string, metadata?: any) => {
        try {
            const response = await fetch(`${API_URL}/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password, ...metadata }),
            })
            const data = await response.json()
            if (!response.ok) {
                return { error: { message: data.message || 'Signup failed' } }
            }
            return { error: null }
        } catch (error) {
            return { error: { message: 'Network error' } }
        }
    }

    const signIn = async (email: string, password: string) => {
        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            })
            const data = await response.json()
            if (!response.ok) {
                return { error: { message: data.message || 'Login failed' } }
            }
            if (data.token) {
                localStorage.setItem('auth_token', data.token)
                setUser(data.user)
            }
            return { error: null }
        } catch (error) {
            return { error: { message: 'Network error' } }
        }
    }

    const signOut = async () => {
        localStorage.removeItem('auth_token')
        setUser(null)
    }

    const value = {
        user,
        loading,
        signUp,
        signIn,
        signOut,
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
