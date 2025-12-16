import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { BackButton } from '@/components/ui/back-button'

export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [accountType, setAccountType] = useState<'business' | 'user'>('business')
    const [phoneNumber, setPhoneNumber] = useState('')
    const { signIn } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        const { error } = await signIn(email, password, {
            accountType,
            phoneNumber: phoneNumber || undefined,
        })

        if (error) {
            setError(error.message)
            setLoading(false)
        } else {
            navigate(accountType === 'business' ? '/dashboard' : '/chat')
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-white">
            <div className="w-full max-w-md p-8">
                <div className="mb-4">
                    <BackButton to="/" />
                </div>
                <div className="mb-8 text-center">
                    <div className="h-12 w-12 bg-brand rounded-lg mx-auto mb-4"></div>
                    <h1 className="text-3xl font-bold text-black">Welcome Back</h1>
                    <p className="text-gray-600 mt-2">
                        {accountType === 'business'
                            ? 'Owner access for managing orders and analytics'
                            : 'User access for chatting and placing orders'}
                    </p>
                </div>

                <div className="mb-6">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Choose account type</p>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { key: 'business', label: 'Business Login' },
                            { key: 'user', label: 'User Login' },
                        ].map(({ key, label }) => (
                            <button
                                key={key}
                                type="button"
                                onClick={() => setAccountType(key as 'business' | 'user')}
                                className={`rounded-lg border px-4 py-3 text-sm font-medium transition-colors ${
                                    accountType === key
                                        ? 'border-brand bg-brand/10 text-brand'
                                        : 'border-gray-200 text-gray-600 hover:text-black'
                                }`}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    {error && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                            {error}
                        </div>
                    )}

                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-black mb-2">
                            Email Address
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                            placeholder="you@example.com"
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-black mb-2">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                            placeholder="••••••••"
                        />
                    </div>

                    {accountType === 'user' && (
                        <div>
                            <label htmlFor="phone" className="block text-sm font-medium text-black mb-2">
                                Phone Number
                            </label>
                            <input
                                id="phone"
                                type="tel"
                                value={phoneNumber}
                                onChange={(e) => setPhoneNumber(e.target.value)}
                                required
                                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                                placeholder="+234..."
                            />
                        </div>
                    )}

                    <Button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-brand hover:bg-brand-600 text-white"
                    >
                        {loading ? 'Signing in...' : 'Sign In'}
                    </Button>
                </form>

                <p className="mt-6 text-center text-sm text-gray-600">
                    Don't have an account?{' '}
                    <Link to="/signup" className="text-brand hover:text-brand-600 font-medium">
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    )
}
