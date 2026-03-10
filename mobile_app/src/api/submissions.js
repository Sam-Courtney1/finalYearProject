import apiClient from './client';

export async function getSubmissions() {
  const response = await apiClient.get('/submissions');
  return response.data;
}

export async function getSubmissionAnswers(submissionId) {
  const response = await apiClient.get(`/submissions/${submissionId}/answers`);
  return response.data;
}

export async function updateSubmissionAnswers(submissionId, fields) {
  const response = await apiClient.put(`/submissions/${submissionId}/answers`, { fields });
  return response.data;
}

export async function deleteSubmission(submissionId) {
  const response = await apiClient.delete(`/submissions/${submissionId}`);
  return response.data;
}
