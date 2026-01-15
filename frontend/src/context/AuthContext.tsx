import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  role: 'admin' | 'editor' | 'viewer';
  tenant_id: string;
  tenant_name?: string;
  is_superuser?: boolean;
  created_at?: string;
}

export interface ImpersonatedUser {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isImpersonating: boolean;
  impersonatedUser: ImpersonatedUser | null;
  impersonatedBy: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, tenantName: string) => Promise<void>;
  logout: () => Promise<void>;
  startImpersonation: (token: string, impersonatedUser: ImpersonatedUser, impersonatedBy: string) => void;
  endImpersonation: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Impersonation state
  const [isImpersonating, setIsImpersonating] = useState(false);
  const [impersonatedUser, setImpersonatedUser] = useState<ImpersonatedUser | null>(null);
  const [impersonatedBy, setImpersonatedBy] = useState<string | null>(null);
  const [originalToken, setOriginalToken] = useState<string | null>(null);

  // Check if user is already logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      const savedOriginalToken = localStorage.getItem('original_token');

      // Check if we're in an impersonation session
      if (savedOriginalToken) {
        setOriginalToken(savedOriginalToken);
        setIsImpersonating(true);
      }

      if (token) {
        try {
          // Verify token and get user info
          const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);

            // If impersonating, set the impersonated user info
            if (savedOriginalToken) {
              setImpersonatedUser({
                id: userData.id,
                email: userData.email,
                first_name: userData.first_name,
                last_name: userData.last_name,
                full_name: userData.full_name,
                role: userData.role,
              });
            }
          } else {
            // Token is invalid, clear it
            localStorage.removeItem('access_token');
            localStorage.removeItem('original_token');
            setIsImpersonating(false);
          }
        } catch (error) {
          console.error('Failed to verify token:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('original_token');
          setIsImpersonating(false);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Create form data for OAuth2 password flow
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);

      // Get user info
      const userResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error('Failed to get user info');
      }

      const userData = await userResponse.json();
      setUser(userData);
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const signup = async (email: string, password: string, tenantName: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          tenant_name: tenantName,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Signup failed');
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);

      // Get user info
      const userResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error('Failed to get user info');
      }

      const userData = await userResponse.json();
      setUser(userData);
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  };

  const logout = async () => {
    // Call backend logout endpoint to log the logout
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }

    localStorage.removeItem('access_token');
    localStorage.removeItem('original_token');
    setUser(null);
    setIsImpersonating(false);
    setImpersonatedUser(null);
    setImpersonatedBy(null);
    setOriginalToken(null);
  };

  const startImpersonation = (token: string, impersonatedUserData: ImpersonatedUser, impersonatedByValue: string) => {
    // Save the original token before impersonating
    const currentToken = localStorage.getItem('access_token');
    if (currentToken) {
      setOriginalToken(currentToken);
      localStorage.setItem('original_token', currentToken);
    }

    // Set the impersonation token
    localStorage.setItem('access_token', token);
    setIsImpersonating(true);
    setImpersonatedUser(impersonatedUserData);
    setImpersonatedBy(impersonatedByValue);

    // Reload to apply the new token
    window.location.reload();
  };

  const endImpersonation = () => {
    // Restore the original token
    const savedOriginalToken = originalToken || localStorage.getItem('original_token');
    if (savedOriginalToken) {
      localStorage.setItem('access_token', savedOriginalToken);
      localStorage.removeItem('original_token');
    }

    setIsImpersonating(false);
    setImpersonatedUser(null);
    setImpersonatedBy(null);
    setOriginalToken(null);

    // Reload to apply the original token
    window.location.reload();
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    isImpersonating,
    impersonatedUser,
    impersonatedBy,
    login,
    signup,
    logout,
    startImpersonation,
    endImpersonation,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
