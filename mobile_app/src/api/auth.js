import apiClient from './client';

export async function loginAPI(username, password) {
  const response = await apiClient.post('/login', { username, password });
  return response.data;
}

export async function registerAPI(username, password, age, address, email) {
  const response = await apiClient.post('/register', { username, password, age, address, email });
  return response.data;
}

export async function logoutAPI() {
  const response = await apiClient.post('/logout');
  return response.data;
}
