import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

// Reads API URL from app.json > expo.extra.apiBaseUrl
// To change: update app.json or set to your computer's LAN IP (run 'ipconfig' to find it)
// Do NOT use 'localhost' — on your phone, localhost means the phone itself.
const API_BASE_URL = Constants.expoConfig?.extra?.apiBaseUrl || 'http://192.168.56.1:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});

// Automatically attach JWT token to every request
apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If a 401 is returned, clear the stored token so the app navigates to login
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response && error.response.status === 401) {
      await AsyncStorage.removeItem('token');
      await AsyncStorage.removeItem('username');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
