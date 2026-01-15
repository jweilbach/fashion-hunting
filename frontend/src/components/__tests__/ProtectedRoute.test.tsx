/**
 * Tests for ProtectedRoute component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import theme from '../../theme/theme'
import ProtectedRoute from '../ProtectedRoute'

// Mock the AuthContext
const mockUseAuth = vi.fn()

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Helper to render with router
function renderWithRouter(
  ui: React.ReactElement,
  { initialEntries = ['/protected'] } = {}
) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route path="/protected" element={ui} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading State', () => {
    it('should show loading spinner when auth is loading', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: true,
      })

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      // Check for CircularProgress (MUI loading spinner has role="progressbar")
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Authentication', () => {
    it('should redirect to login when not authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      // Should redirect to login page
      expect(screen.getByText('Login Page')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('should render children when authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'editor' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })
  })

  describe('Role-Based Access', () => {
    it('should allow access when user role meets requirement', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'admin' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute requiredRole="editor">
          <div>Editor Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Editor Content')).toBeInTheDocument()
    })

    it('should allow access when user role exactly matches requirement', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'editor' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute requiredRole="editor">
          <div>Editor Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Editor Content')).toBeInTheDocument()
    })

    it('should redirect to dashboard when user role is insufficient', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'viewer' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    })

    it('should allow viewer to access viewer-level routes', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'viewer' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute requiredRole="viewer">
          <div>Viewer Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Viewer Content')).toBeInTheDocument()
    })
  })

  describe('Role Hierarchy', () => {
    it('admin should have access to all roles', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'admin' },
        isAuthenticated: true,
        isLoading: false,
      })

      // Admin accessing viewer content
      const { rerender } = renderWithRouter(
        <ProtectedRoute requiredRole="viewer">
          <div>Content</div>
        </ProtectedRoute>
      )
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('editor should not have access to admin routes', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'editor' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })
  })
})
