import apiClient from './client';

export async function getClients() {
  const response = await apiClient.get('/clients');
  return response.data;
}

export async function getQuestionnaireFields(clientId, questionnaireName) {
  const response = await apiClient.get(
    `/questionnaire/${clientId}/${encodeURIComponent(questionnaireName)}`
  );
  return response.data;
}

export async function submitQuestionnaire(clientId, questionnaireName, fields, consent) {
  const response = await apiClient.post(
    `/questionnaire/${clientId}/${encodeURIComponent(questionnaireName)}`,
    { fields, consent }
  );
  return response.data;
}
