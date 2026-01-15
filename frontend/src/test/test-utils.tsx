/**
 * Test Utilities
 *
 * Custom render function and utilities for testing React components
 * with all the necessary providers (Router, Query, Theme, Auth).
 */
import type { ReactElement, ReactNode } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import theme from '../theme/theme'
import { AuthProvider } from '../context/AuthContext'

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface AllProvidersProps {
  children: ReactNode
  initialEntries?: string[]
}

/**
 * Wrapper component that provides all context providers
 */
function AllProviders({ children, initialEntries = ['/'] }: AllProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MemoryRouter initialEntries={initialEntries}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
}

/**
 * Custom render function that wraps component with all providers
 *
 * Usage:
 * ```
 * import { renderWithProviders } from '@/test/test-utils'
 *
 * test('renders component', () => {
 *   renderWithProviders(<MyComponent />)
 * })
 * ```
 */
function renderWithProviders(
  ui: ReactElement,
  { initialEntries = ['/'], ...options }: CustomRenderOptions = {}
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders initialEntries={initialEntries}>{children}</AllProviders>
    ),
    ...options,
  })
}

/**
 * Render with just the theme provider (for testing isolated components)
 */
function renderWithTheme(ui: ReactElement, options?: RenderOptions) {
  return render(ui, {
    wrapper: ({ children }) => (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    ),
    ...options,
  })
}

/**
 * Render with QueryClient only (for testing hooks/data fetching)
 */
function renderWithQuery(ui: ReactElement, options?: RenderOptions) {
  const queryClient = createTestQueryClient()

  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    ),
    ...options,
  })
}

/**
 * Wait for loading states to resolve
 */
async function waitForLoadingToFinish() {
  // Wait for any pending React updates
  await new Promise(resolve => setTimeout(resolve, 0))
}

/**
 * Create mock user for auth testing
 */
function createMockUser(overrides = {}) {
  return {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    role: 'editor',
    tenant_id: 'tenant-123',
    ...overrides,
  }
}

/**
 * Create mock report for testing
 */
function createMockReport(overrides = {}) {
  return {
    id: `report-${Math.random().toString(36).substring(7)}`,
    title: 'Test Report Title',
    source: 'Test Source',
    provider: 'google_search',
    link: 'https://example.com/article',
    timestamp: new Date().toISOString(),
    summary: 'This is a test summary.',
    sentiment: 'positive' as const,
    brands: ['Brand A', 'Brand B'],
    est_reach: 50000,
    ...overrides,
  }
}

/**
 * Create mock list for testing
 */
function createMockList(overrides = {}) {
  return {
    id: `list-${Math.random().toString(36).substring(7)}`,
    name: 'Test List',
    list_type: 'report',
    description: 'A test list',
    item_count: 5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { userEvent } from '@testing-library/user-event'

// Export custom utilities
export {
  renderWithProviders,
  renderWithTheme,
  renderWithQuery,
  waitForLoadingToFinish,
  createMockUser,
  createMockReport,
  createMockList,
  createTestQueryClient,
}
