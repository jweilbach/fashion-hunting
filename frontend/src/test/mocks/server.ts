/**
 * MSW Server Setup
 *
 * Creates a mock server that intercepts network requests during tests.
 */
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Setup request interception using the given handlers
export const server = setupServer(...handlers)
