/**
 * Tests for the AuthContext and AuthProvider
 *
 * These tests verify the authentication context behavior including:
 * - Initial state and loading
 * - Login flow
 * - Signup flow
 * - Logout functionality
 * - Token persistence
 *
 * Uses MSW (Mock Service Worker) for API mocking, consistent with project standards.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/mocks/server'
import { createHandler } from '../../test/mocks/handlers'
import { AuthProvider, useAuth } from '../AuthContext'

// Create a localStorage mock that persists state between calls
const createLocalStorageMock = () => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    // Test helper methods
    _reset: () => {
      store = {}
    },
    _setInitialToken: (token: string) => {
      store['access_token'] = token
    },
  }
}

const localStorageMock = createLocalStorageMock()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Test component that exposes auth context state and actions
function TestAuthConsumer() {
  const { user, isAuthenticated, isLoading, login, logout, signup } = useAuth()

  const handleLogin = async () => {
    try {
      await login('test@example.com', 'password123')
    } catch {
      // Errors logged by AuthContext
    }
  }

  const handleSignup = async () => {
    try {
      await signup('new@example.com', 'password123', 'New Company')
    } catch {
      // Errors logged by AuthContext
    }
  }

  if (isLoading) {
    return <div data-testid="loading">Loading...</div>
  }

  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      {user && <div data-testid="user-email">{user.email}</div>}
      {user && <div data-testid="user-role">{user.role}</div>}
      <button onClick={handleLogin} data-testid="login-btn">
        Login
      </button>
      <button onClick={handleSignup} data-testid="signup-btn">
        Signup
      </button>
      <button onClick={logout} data-testid="logout-btn">
        Logout
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock._reset()
  })

  afterEach(() => {
    server.resetHandlers()
  })

  describe('useAuth hook', () => {
    it('throws error when used outside AuthProvider', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        render(<TestAuthConsumer />)
      }).toThrow('useAuth must be used within an AuthProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('initial authentication state', () => {
    it('shows loading state while checking auth with token', async () => {
      // When there's a token, the context must verify it asynchronously
      // We can use a delayed handler to capture the loading state
      let resolveHandler: (() => void) | null = null
      const delayedPromise = new Promise<void>((resolve) => {
        resolveHandler = resolve
      })

      server.use(
        http.get('*/api/v1/auth/me', async () => {
          await delayedPromise
          return HttpResponse.json({
            id: 'user-123',
            email: 'test@example.com',
            role: 'editor',
            tenant_id: 'tenant-123',
          })
        })
      )

      localStorageMock._setInitialToken('valid-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      // Should show loading while waiting for auth check
      expect(screen.getByTestId('loading')).toBeInTheDocument()

      // Resolve the handler and wait for auth to complete
      resolveHandler!()

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
    })

    it('is not authenticated when no token exists', async () => {
      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      expect(screen.getByTestId('auth-status')).toHaveTextContent('not-authenticated')
    })

    it('verifies existing token and authenticates user', async () => {
      // Set token before render
      localStorageMock._setInitialToken('valid-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
      })

      // Default MSW handler returns test user
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com')
      expect(screen.getByTestId('user-role')).toHaveTextContent('editor')
    })

    it('clears invalid token and shows unauthenticated', async () => {
      // Override handler to return 401 using environment-aware helper
      server.use(
        ...createHandler('get', '/auth/me', () =>
          HttpResponse.json({ detail: 'Invalid token' }, { status: 401 })
        )
      )

      localStorageMock._setInitialToken('invalid-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('not-authenticated')
      })

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
    })
  })

  describe('login', () => {
    it('authenticates user on successful login', async () => {
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'mock-jwt-token')
    })

    it('remains unauthenticated on login failure', async () => {
      // Override handler using environment-aware helper
      server.use(
        ...createHandler('post', '/auth/token', () =>
          HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
        )
      )

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      // Give time for the login attempt to complete
      await new Promise((resolve) => setTimeout(resolve, 100))

      expect(screen.getByTestId('auth-status')).toHaveTextContent('not-authenticated')

      consoleSpy.mockRestore()
    })
  })

  describe('signup', () => {
    it('authenticates user on successful signup', async () => {
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      await user.click(screen.getByTestId('signup-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'mock-signup-token')
    })

    it('remains unauthenticated on signup failure', async () => {
      // Override handler using environment-aware helper
      server.use(
        ...createHandler('post', '/auth/signup', () =>
          HttpResponse.json({ detail: 'Email already exists' }, { status: 400 })
        )
      )

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('loading')).not.toBeInTheDocument()
      })

      await user.click(screen.getByTestId('signup-btn'))

      // Give time for the signup attempt to complete
      await new Promise((resolve) => setTimeout(resolve, 100))

      expect(screen.getByTestId('auth-status')).toHaveTextContent('not-authenticated')

      consoleSpy.mockRestore()
    })
  })

  describe('logout', () => {
    it('clears user and token on logout', async () => {
      localStorageMock._setInitialToken('user-token')

      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
      })

      await user.click(screen.getByTestId('logout-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('not-authenticated')
      })

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
    })
  })
})
