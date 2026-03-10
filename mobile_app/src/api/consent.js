import apiClient from './client';

export async function getConsentStatus() {
  const response = await apiClient.get('/consent');
  return response.data;
}

export async function withdrawConsent(submissionId) {
  const response = await apiClient.post(`/submissions/${submissionId}/consent/withdraw`);
  return response.data;
}

export async function reinstateConsent(submissionId) {
  const response = await apiClient.post(`/submissions/${submissionId}/consent/reinstate`);
  return response.data;
}
