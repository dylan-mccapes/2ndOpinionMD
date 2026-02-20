import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RoleProtectedRoute } from './components/RoleProtectedRoute';
import { HomePage } from './pages/HomePage';
import { AskPage } from './pages/AskPage';
import { CodingPage } from './pages/CodingPage';
import { EohPage } from './pages/EohPage';
import { EohdPage } from './pages/EohdPage';
import { JournalPage } from './pages/JournalPage';
import { PatientPortalPage } from './pages/PatientPortalPage';
import { DoctorPortalPage } from './pages/DoctorPortalPage';
import { DoctorPatientDetailPage } from './pages/DoctorPatientDetailPage';
import { SettingsPage } from './pages/SettingsPage';
import { TimelineUploadPage } from './pages/TimelineUploadPage';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { VerifyPage } from './pages/auth/VerifyPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { NotFoundPage } from './pages/NotFoundPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/ask" element={<ProtectedRoute><AskPage /></ProtectedRoute>} />
          <Route path="/coding" element={<ProtectedRoute><CodingPage /></ProtectedRoute>} />
          <Route path="/eoh" element={<ProtectedRoute><EohPage /></ProtectedRoute>} />
          <Route path="/eohd" element={<ProtectedRoute><EohdPage /></ProtectedRoute>} />
          <Route path="/journal" element={<RoleProtectedRoute role="patient"><JournalPage /></RoleProtectedRoute>} />
          <Route path="/patient" element={<RoleProtectedRoute role="patient"><PatientPortalPage /></RoleProtectedRoute>} />
          <Route path="/timeline/upload" element={<RoleProtectedRoute role="patient"><TimelineUploadPage /></RoleProtectedRoute>} />
          <Route path="/doctor" element={<RoleProtectedRoute role="doctor"><DoctorPortalPage /></RoleProtectedRoute>} />
          <Route path="/doctor/patients/:patientId" element={<RoleProtectedRoute role="doctor"><DoctorPatientDetailPage /></RoleProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />
          <Route path="/auth/verify" element={<VerifyPage />} />
          <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/auth/reset-password/:token" element={<ResetPasswordPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
