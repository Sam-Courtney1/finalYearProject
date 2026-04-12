import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  BackHandler,
  Linking,
  Platform,
  StyleSheet,
  View,
  Text,
  ActivityIndicator,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { WebView } from 'react-native-webview';
import Constants from 'expo-constants';
import * as SplashScreen from 'expo-splash-screen';

SplashScreen.preventAutoHideAsync();

const WEBSITE_URL =
  Constants.expoConfig?.extra?.websiteUrl ||
  'https://03-test.eba-imv8cadf.eu-west-1.elasticbeanstalk.com'; // Configure per-environment via app.json extra.websiteUrl

const APP_HOSTNAME = new URL(WEBSITE_URL).hostname;

export default function App() {
  const webViewRef = useRef(null);
  const [canGoBack, setCanGoBack] = useState(false);
  // Hide splash screen once the WebView has loaded
  const onLoadEnd = useCallback(() => {
    SplashScreen.hideAsync();
  }, []);

  // Android hardware back button
  useEffect(() => {
    if (Platform.OS !== 'android') return;

    const handler = BackHandler.addEventListener('hardwareBackPress', () => {
      if (canGoBack && webViewRef.current) {
        webViewRef.current.goBack();
        return true;
      }
      return false;
    });

    return () => handler.remove();
  }, [canGoBack]);

  // Track navigation state for back button
  const onNavigationStateChange = useCallback((navState) => {
    setCanGoBack(navState.canGoBack);
  }, []);

  // Only allow navigation within the app's domain (plus CDN resources)
  const onShouldStartLoadWithRequest = useCallback((request) => {
    const url = request.url;

    // Open mailto/tel links in the device's default app
    if (url.startsWith('mailto:') || url.startsWith('tel:')) {
      Linking.openURL(url);
      return false;
    }

    // Allow the main site, data URIs, and about:blank
    if (
      url.startsWith('about:') ||
      url.startsWith('data:') ||
      url.includes(APP_HOSTNAME)
    ) {
      return true;
    }

    // Allow common CDN resources (fonts, Bootstrap, etc.) to load
    const allowedHosts = [
      'fonts.googleapis.com',
      'fonts.gstatic.com',
      'cdn.jsdelivr.net',
      'unpkg.com',
      'cdnjs.cloudflare.com',
    ];
    try {
      const host = new URL(url).hostname;
      if (allowedHosts.some((h) => host.endsWith(h))) {
        return true;
      }
    } catch {
      return false;
    }

    // Block other external navigation (would take user away from the app)
    return false;
  }, []);

  const reload = useCallback(() => {
    if (webViewRef.current) {
      webViewRef.current.reload();
    }
  }, []);

  const renderError = useCallback(() => {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorIcon}>!</Text>
        <Text style={styles.errorTitle}>No Connection</Text>
        <Text style={styles.errorMessage}>
          Could not reach the server. Check your internet connection and try
          again.
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={reload}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }, [reload]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />

      <WebView
        ref={webViewRef}
        source={{ uri: WEBSITE_URL }}
        style={styles.webview}
        onLoadEnd={onLoadEnd}
        onNavigationStateChange={onNavigationStateChange}
        onShouldStartLoadWithRequest={onShouldStartLoadWithRequest}
        renderError={renderError}
        onError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.error('WebView error:', nativeEvent);
        }}
        javaScriptEnabled
        domStorageEnabled
        sharedCookiesEnabled
        thirdPartyCookiesEnabled={false}
        allowsBackForwardNavigationGestures
        pullToRefreshEnabled
        setSupportMultipleWindows={false}
        startInLoadingState
        renderLoading={() => (
          <View style={styles.loadingOverlay}>
            <ActivityIndicator size="large" color="#7c3aed" />
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  webview: {
    flex: 1,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorContainer: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorIcon: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#7c3aed',
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  retryButton: {
    backgroundColor: '#7c3aed',
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 8,
  },
  retryText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
