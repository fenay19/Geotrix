import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

interface User {
  id: number;
  email: string;
  name?: string;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  session: string | null;
  loading: boolean;
  login: (email: string, token: string, userData: User) => void;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<string | null>(localStorage.getItem('geotrade_token'));
  const [loading, setLoading] = useState<boolean>(true);

  const checkSession = async () => {
    const token = localStorage.getItem('geotrade_token');
    if (!token) {
      setUser(null);
      setSession(null);
      setLoading(false);
      return;
    }

    try {
      // Set the global default Authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      const res = await axios.get(`${API_BASE}/auth/me`);
      if (res.data) {
        setUser(res.data);
        setSession(token);
      } else {
        throw new Error('Invalid session response');
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        // Backend responded — token is invalid/expired; clear the session
        localStorage.removeItem('geotrade_token');
        delete axios.defaults.headers.common['Authorization'];
        setUser(null);
        setSession(null);
      } else {
        // Network error / server unreachable — keep the token so the user
        // isn't logged out just because the server is temporarily down.
        console.warn('Session check failed due to network error; retaining stored token.', err);
        setSession(token);
        // user stays null until a successful /me response
      }
    } finally {
      setLoading(false);
    }
  };

  const login = (_email: string, token: string, userData: User) => {
    localStorage.setItem('geotrade_token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setSession(token);
    setUser(userData);
  };

  // Define logout before the ref so there is no TDZ issue
  const logout = useCallback(async () => {
    try {
      await axios.post(`${API_BASE}/auth/logout`);
    } catch (err) {
      console.warn('Logout endpoint failed:', err);
    } finally {
      localStorage.removeItem('geotrade_token');
      delete axios.defaults.headers.common['Authorization'];
      setSession(null);
      setUser(null);
    }
  }, []);

  // Stable ref so the interceptor always calls the latest logout without re-registering
  const logoutRef = useRef(logout);
  useEffect(() => {
    logoutRef.current = logout;
  }, [logout]);

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    // Add interceptor to handle 401 errors globally (e.g. token expiration)
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          const isAuthRequest = error.config?.url && (
            error.config.url.includes('/auth/login') ||
            error.config.url.includes('/auth/register') ||
            error.config.url.includes('/auth/forgot-password') ||
            error.config.url.includes('/auth/reset-password') ||
            error.config.url.includes('/auth/logout')
          );
          if (!isAuthRequest) {
            console.warn('Session expired or unauthorized (401). Logging out...');
            logoutRef.current();
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  return (
    <AuthContext.Provider value={{ user, session, loading, login, logout, checkSession }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
