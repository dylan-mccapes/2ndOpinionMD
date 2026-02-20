import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { AskPage } from './pages/AskPage';
import { CodingPage } from './pages/CodingPage';
import { EohPage } from './pages/EohPage';
import { EohdPage } from './pages/EohdPage';
import { JournalPage } from './pages/JournalPage';
import { PortalPage } from './pages/PortalPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { VerifyPage } from './pages/auth/VerifyPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/ask" element={<AskPage />} />
          <Route path="/coding" element={<CodingPage />} />
          <Route path="/eoh" element={<EohPage />} />
          <Route path="/eohd" element={<EohdPage />} />
          <Route path="/journal" element={<JournalPage />} />
          <Route path="/portal" element={<PortalPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />
          <Route path="/auth/verify" element={<VerifyPage />} />
          <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/auth/reset-password/:token" element={<ResetPasswordPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
