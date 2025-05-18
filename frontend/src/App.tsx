import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { ApiProvider } from './contexts/ApiContext';
import { AuthProvider } from './contexts/AuthContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { RouterProvider } from './contexts/RouterContext';
import { GeolocationProvider } from './contexts/GeolocationContext';
import { MouseProvider } from './contexts/MouseContext';
import AppRoutes from './routes';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <NotificationProvider>
        <ApiProvider>
          <AuthProvider>
            <LanguageProvider>
              <RouterProvider>
                <GeolocationProvider>
                  <MouseProvider>
                    <AppRoutes />
                  </MouseProvider>
                </GeolocationProvider>
              </RouterProvider>
            </LanguageProvider>
          </AuthProvider>
        </ApiProvider>
      </NotificationProvider>
    </BrowserRouter>
  );
};

export default App;
