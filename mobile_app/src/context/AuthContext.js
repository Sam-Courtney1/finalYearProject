import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // On app launch, check for an existing token in storage
  useEffect(() => {
    async function loadToken() {
      try {
        const storedToken = await AsyncStorage.getItem('token');
        const storedUsername = await AsyncStorage.getItem('username');
        if (storedToken) {
          setToken(storedToken);
          setUsername(storedUsername);
        }
      } catch (e) {
        // Storage read failed — treat as logged out
      }
      setIsLoading(false);
    }
    loadToken();
  }, []);

  async function login(newToken, newUsername) {
    await AsyncStorage.setItem('token', newToken);
    await AsyncStorage.setItem('username', newUsername);
    setToken(newToken);
    setUsername(newUsername);
  }

  async function logout() {
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('username');
    setToken(null);
    setUsername(null);
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        username,
        isLoggedIn: !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
