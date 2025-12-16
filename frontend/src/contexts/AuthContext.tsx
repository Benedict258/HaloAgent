import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface User {
    id: string
    email: string
    phone_number: string
    first_name: string
    last_name: string
    business_name?: string | null
    business_id?: string | null
    account_type: 'business' | 'user'
    preferred_language?: string | null
    is_verified?: boolean | null
    created_at: string
    [key: string]: unknown
}

interface AuthError {
    message: string
}

interface SignInOptions {
    accountType?: 'business' | 'user'
    phoneNumber?: string
}

interface SignUpMetadata {
    account_type?: 'business' | 'user'
    phone_number?: string
    first_name?: string
    last_name?: string
    business_name?: string
    business_handle?: string
}

interface AuthContextType {
    user: User | null
    loading: boolean
    signUp: (email: string, password: string, metadata?: SignUpMetadata) => Promise<{ error: AuthError | null }>
    signIn: (email: string, password: string, options?: SignInOptions) => Promise<{ error: AuthError | null }>
    signOut: () => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL || 'https://haloagent.onrender.com'

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
            .then(res => {
                if (res.ok) return res.json()
                throw new Error('Invalid token')
            })
            .then((data: User) => {
                setUser(data)
                if (data.account_type === 'user' && data.phone_number) {
                    localStorage.setItem('user_phone', data.phone_number)
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

    const signUp = async (email: string, password: string, metadata?: SignUpMetadata) => {
        try {
            const accountType = metadata?.account_type ?? 'business'
            const trimmedFirstName = metadata?.first_name?.trim()
            const trimmedLastName = metadata?.last_name?.trim()

            const payload = {
                email,
                password,
                phone_number: metadata?.phone_number || '+234000000000',
                first_name: trimmedFirstName || (accountType === 'business' ? 'Business' : 'User'),
                last_name: trimmedLastName || (accountType === 'business' ? 'Owner' : 'Customer'),
                business_name: accountType === 'business'
                    ? (metadata?.business_name || 'New Business')
                    : undefined,
                account_type: accountType,
                business_handle: metadata?.business_handle
            }
            
            const response = await fetch(`${API_URL}/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            const data = await response.json()
            if (!response.ok) {
                const errorMsg = data.detail || (Array.isArray(data.detail) ? data.detail[0].msg : 'Signup failed')
                return { error: { message: errorMsg } }
            }
            if (data.access_token) {
                localStorage.setItem('auth_token', data.access_token)
                // Fetch user profile
                const userRes = await fetch(`${API_URL}/auth/me`, {
                    headers: { 'Authorization': `Bearer ${data.access_token}` }
                })
                const userData: User = await userRes.json()
                setUser(userData)
                if (userData.account_type === 'user' && userData.phone_number) {
                    localStorage.setItem('user_phone', userData.phone_number)
                }
            }
            return { error: null }
        } catch (error) {
            return { error: { message: 'Network error' } }
        }
    }

    const signIn = async (email: string, password: string, options?: SignInOptions) => {
        try {
            const payload = {
                email,
                password,
                account_type: options?.accountType
            }
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            const data = await response.json()
            if (!response.ok) {
                return { error: { message: data.detail || 'Login failed' } }
            }
            if (data.access_token) {
                localStorage.setItem('auth_token', data.access_token)
                // Fetch user profile
                const userRes = await fetch(`${API_URL}/auth/me`, {
                    headers: { 'Authorization': `Bearer ${data.access_token}` }
                })
                const userData: User = await userRes.json()
                setUser(userData)

                if (userData.account_type === 'user') {
                    const phone = options?.phoneNumber || userData.phone_number
                    if (phone) {
                        localStorage.setItem('user_phone', phone)
                    }
                }
            }
            return { error: null }
        } catch (error) {
            return { error: { message: 'Network error' } }
        }
    }

    const signOut = async () => {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_phone')
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
