import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { BackButton } from '@/components/ui/back-button'

export default function SignUpPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [businessName, setBusinessName] = useState('')
    const [businessHandle, setBusinessHandle] = useState('')
    const [phoneNumber, setPhoneNumber] = useState('')
    const [firstName, setFirstName] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [accountType, setAccountType] = useState<'business' | 'user'>('business')
    const { signUp } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters')
            return
        }

        if (accountType === 'business' && !businessName.trim()) {
            setError('Business name is required for business accounts')
            return
        }

        if (accountType === 'user' && !phoneNumber.trim()) {
            setError('Phone number is required for user accounts')
            return
        }

        setLoading(true)

        const { error } = await signUp(email, password, {
            business_name: accountType === 'business' ? businessName : undefined,
            phone_number: phoneNumber || undefined,
            account_type: accountType,
            first_name: firstName.trim() || undefined,
            business_handle:
                accountType === 'business' && businessHandle.trim() ? businessHandle.trim() : undefined,
        })

        if (error) {
            setError(error.message)
            setLoading(false)
            return
        }

        if (accountType === 'user' && phoneNumber.trim()) {
            localStorage.setItem('user_phone', phoneNumber.trim())
        }

        setSuccess(true)
        setTimeout(() => navigate('/login'), 2000)
    }

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-white">
                <div className="w-full max-w-md p-8 text-center">
                    <div className="h-16 w-16 bg-green-100 rounded-full mx-auto mb-4 flex items-center justify-center">
                        <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-black mb-2">Account Created!</h2>
                    <p className="text-gray-600">Check your email to verify your account. Redirecting to login...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-white py-12">
            <div className="w-full max-w-md p-8">
                <div className="mb-4">
                    <BackButton to="/" />
                </div>

                <div className="mb-8 text-center">
                    <div className="h-12 w-12 bg-brand rounded-lg mx-auto mb-4"></div>
                    <h1 className="text-3xl font-bold text-black">Create Account</h1>
                    <p className="text-gray-600 mt-2">
                        {accountType === 'business'
                            ? 'Start managing your business with AI'
                            : 'Sign up to chat with businesses and track orders'}
                    </p>
                </div>

                <div className="mb-6">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">I am signing up as</p>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { key: 'business', label: 'Business Owner' },
                            { key: 'user', label: 'User' },
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

                <form onSubmit={handleSubmit} className="space-y-5">
                    {error && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                            {error}
                        </div>
                    )}

                    {accountType === 'business' && (
                        <div>
                            <label htmlFor="businessName" className="block text-sm font-medium text-black mb-2">
                                Business Name
                            </label>
                            <input
                                id="businessName"
                                type="text"
                                value={businessName}
                                onChange={(e) => setBusinessName(e.target.value)}
                                required
                                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                                placeholder="Your Business Name"
                            />
                        </div>
                    )}

                    <div>
                        <label htmlFor="firstName" className="block text-sm font-medium text-black mb-2">
                            First Name
                        </label>
                        <input
                            id="firstName"
                            type="text"
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                            placeholder="Ada"
                        />
                    </div>

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
                        <label htmlFor="phoneNumber" className="block text-sm font-medium text-black mb-2">
                            Phone Number {accountType === 'user' ? '' : '(optional)'}
                        </label>
                        <input
                            id="phoneNumber"
                            type="tel"
                            value={phoneNumber}
                            onChange={(e) => setPhoneNumber(e.target.value)}
                            required={accountType === 'user'}
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                            placeholder="+234..."
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

                    <div>
                        <label htmlFor="confirmPassword" className="block text-sm font-medium text-black mb-2">
                            Confirm Password
                        </label>
                        <input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                            placeholder="••••••••"
                        />
                    </div>

                    {accountType === 'business' && (
                        <div>
                            <label htmlFor="businessHandle" className="block text-sm font-medium text-black mb-2">
                                Business Username / ID (optional)
                            </label>
                            <input
                                id="businessHandle"
                                type="text"
                                value={businessHandle}
                                onChange={(e) => setBusinessHandle(e.target.value)}
                                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                                placeholder="e.g. sweetcrumbs"
                            />
                            <p className="text-xs text-gray-500 mt-1">Used as your business ID in the web app.</p>
                        </div>
                    )}

                    <Button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-brand hover:bg-brand-600 text-white"
                    >
                        {loading ? 'Creating account...' : 'Create Account'}
                    </Button>
                </form>

                <p className="mt-6 text-center text-sm text-gray-600">
                    Already have an account?{' '}
                    <Link to="/login" className="text-brand hover:text-brand-600 font-medium">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    )
}
