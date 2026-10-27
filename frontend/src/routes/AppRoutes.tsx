import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { AppShell } from "../components/AppShell";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { ComplaintsPage } from "../pages/ComplaintsPage";
import { ComplaintCreatePage } from "../pages/ComplaintCreatePage";
import { ComplaintDetailPage } from "../pages/ComplaintDetailPage";
import { RelationsQueuePage } from "../pages/RelationsQueuePage";
import { InstitutionsPage } from "../pages/InstitutionsPage";
import { InstitutionDetailPage } from "../pages/InstitutionDetailPage";
import { ReportsPage } from "../pages/ReportsPage";
import { NotificationsPage } from "../pages/NotificationsPage";
import { UsersAdminPage } from "../pages/UsersAdminPage";
import { AuditLogsAdminPage } from "../pages/AuditLogsAdminPage";
import { UnauthorizedPage, NotFoundPage } from "../pages/ErrorPages";

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Login Route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes inside AppShell */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/complaints" element={<ComplaintsPage />} />
        <Route path="/complaints/new" element={<ComplaintCreatePage />} />
        <Route path="/complaints/:id" element={<ComplaintDetailPage />} />
        <Route path="/relations" element={<RelationsQueuePage />} />
        <Route path="/institutions" element={<InstitutionsPage />} />
        <Route path="/institutions/:id" element={<InstitutionDetailPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />

        {/* Administration Routes (System Admin only) */}
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute roles={["SYSTEM_ADMIN"]}>
              <UsersAdminPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <ProtectedRoute roles={["SYSTEM_ADMIN"]}>
              <AuditLogsAdminPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Error Routes */}
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
