import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { colors } from './src/theme/theme';

import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import DataAccessScreen from './src/screens/DataAccessScreen';
import QuestionnaireSelectScreen from './src/screens/QuestionnaireSelectScreen';
import QuestionnaireScreen from './src/screens/QuestionnaireScreen';
import SubmissionsListScreen from './src/screens/SubmissionsListScreen';
import EditSubmissionScreen from './src/screens/EditSubmissionScreen';
import ConsentManagementScreen from './src/screens/ConsentManagementScreen';
import SettingsScreen from './src/screens/SettingsScreen';

const Stack = createNativeStackNavigator();

const headerStyle = {
  headerStyle: { backgroundColor: colors.primary },
  headerTintColor: '#fff',
  headerTitleStyle: { fontWeight: 'bold' },
};

function AppNavigator() {
  const { isLoggedIn, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <Stack.Navigator screenOptions={headerStyle}>
      {isLoggedIn ? (
        <>
          <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'GDPR Compliance' }} />
          <Stack.Screen name="DataAccess" component={DataAccessScreen} options={{ title: 'Your Data' }} />
          <Stack.Screen name="QuestionnaireSelect" component={QuestionnaireSelectScreen} options={{ title: 'Select Organisation' }} />
          <Stack.Screen name="Questionnaire" component={QuestionnaireScreen} options={{ title: 'Questionnaire' }} />
          <Stack.Screen name="Submissions" component={SubmissionsListScreen} options={{ title: 'My Submissions' }} />
          <Stack.Screen name="EditSubmission" component={EditSubmissionScreen} options={{ title: 'Edit Answers' }} />
          <Stack.Screen name="ConsentManagement" component={ConsentManagementScreen} options={{ title: 'Manage Consent' }} />
          <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
        </>
      ) : (
        <>
          <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'Create Account', ...headerStyle }} />
        </>
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
