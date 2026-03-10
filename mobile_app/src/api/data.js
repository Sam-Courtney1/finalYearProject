import apiClient from './client';

export async function getUserData() {
  const response = await apiClient.get('/user/data');
  return response.data;
}

export async function deleteAccount() {
  const response = await apiClient.delete('/user/account');
  return response.data;
}

export async function deleteUserData() {
  const response = await apiClient.delete('/user/data');
  return response.data;
}
