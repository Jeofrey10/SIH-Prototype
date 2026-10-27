import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, KeyRound, CheckCircle, Ban } from "lucide-react";
import { usersApi, bureausApi } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import { BureauChip } from "../components/Badges";
import { ConfirmModal } from "../components/ConfirmModal";

export const UsersAdminPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Modals state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);

  // New user form state
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("RB_OFFICIAL");
  const [bureauCode, setBureauCode] = useState("RB");
  const [designation, setDesignation] = useState("");
  const [initialPassword, setInitialPassword] = useState("");

  const [newPassword, setNewPassword] = useState("");

  const { data: bureausData } = useQuery({
    queryKey: ["bureaus-list"],
    queryFn: () => bureausApi.list(),
  });

  const { data: usersData, isLoading } = useQuery({
    queryKey: ["admin-users", page, pageSize],
    queryFn: () => usersApi.list({ page, page_size: pageSize }),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      usersApi.create({
        email,
        full_name: fullName,
        role: role as any,
        bureau_code: role === "SUPERVISOR" || role === "SYSTEM_ADMIN" ? null : bureauCode,
        designation,
        password: initialPassword,
      }),
    onSuccess: () => {
      setCreateModalOpen(false);
      setEmail("");
      setFullName("");
      setInitialPassword("");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err: any) => {
      alert("Failed to create user: " + err.message);
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (u: any) =>
      u.is_active ? usersApi.deactivate(u.id) : usersApi.activate(u.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err: any) => {
      alert("Failed to update status: " + err.message);
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: () =>
      usersApi.resetPassword(selectedUser.id, { new_password: newPassword }),
    onSuccess: () => {
      setResetModalOpen(false);
      setNewPassword("");
      setSelectedUser(null);
      alert("Password has been reset successfully.");
    },
    onError: (err: any) => {
      alert("Failed to reset password: " + err.message);
    },
  });

  const columns: Column<any>[] = [
    {
      header: "Official Name & Email",
      accessorKey: "full_name",
      className: "font-semibold text-xs text-surface-text",
      cell: (row) => (
        <div>
          <div>{row.full_name}</div>
          <div className="text-[11px] text-surface-subtle font-normal">
            {row.email}
          </div>
        </div>
      ),
    },
    {
      header: "Role",
      accessorKey: "role",
      className: "w-36 text-xs",
      cell: (row) => (
        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-muted border border-surface-border font-medium">
          {row.role}
        </span>
      ),
    },
    {
      header: "Bureau",
      accessorKey: "bureau_code",
      className: "w-28 text-center",
      cell: (row) => (row.bureau_code ? <BureauChip code={row.bureau_code} /> : "—"),
    },
    {
      header: "Designation",
      accessorKey: "designation",
      className: "w-44 text-xs text-surface-subtle",
    },
    {
      header: "Status",
      accessorKey: "is_active",
      className: "w-24 text-center",
      cell: (row) => (
        <span
          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
            row.is_active
              ? "bg-emerald-100 text-emerald-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {row.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      header: "Actions",
      className: "w-36 text-right",
      cell: (row) => (
        <div className="flex items-center justify-end gap-1.5">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedUser(row);
              setResetModalOpen(true);
            }}
            className="p-1.5 rounded text-surface-subtle hover:text-brand-600 hover:bg-surface-muted"
            title="Reset Password"
          >
            <KeyRound className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              toggleActiveMutation.mutate(row);
            }}
            className={`p-1.5 rounded ${
              row.is_active
                ? "text-surface-subtle hover:text-red-600"
                : "text-surface-subtle hover:text-emerald-600"
            } hover:bg-surface-muted`}
            title={row.is_active ? "Deactivate User" : "Activate User"}
          >
            {row.is_active ? (
              <Ban className="w-3.5 h-3.5" />
            ) : (
              <CheckCircle className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Official Accounts &amp; RBAC Directory
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            Manage system administrators, bureau supervisors, and assigned case officials
          </p>
        </div>

        <button
          type="button"
          onClick={() => setCreateModalOpen(true)}
          className="gov-btn-primary text-sm py-2 px-4 shadow-sm flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" />
          <span>Add Official User</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={usersData?.items || []}
        totalCount={usersData?.total || 0}
        page={page}
        pageSize={pageSize}
        isLoading={isLoading}
        onPageChange={(p) => setPage(p)}
      />

      {/* CREATE USER MODAL */}
      <ConfirmModal
        isOpen={createModalOpen}
        title="Create New Official User"
        confirmLabel="Create User"
        isLoading={createMutation.isPending}
        onConfirm={() => createMutation.mutate()}
        onClose={() => setCreateModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="uName">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              id="uName"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Dr. S. K. Sharma"
              className="gov-input text-xs"
            />
          </div>

          <div>
            <label className="gov-label" htmlFor="uEmail">
              Official Email <span className="text-red-500">*</span>
            </label>
            <input
              id="uEmail"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="official@aicte.gov.in"
              className="gov-input text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="gov-label" htmlFor="uRole">
                Role Classification
              </label>
              <select
                id="uRole"
                value={role}
                onChange={(e) => {
                  setRole(e.target.value);
                  if (e.target.value === "RB_OFFICIAL") setBureauCode("RB");
                  if (e.target.value === "PGRC_OFFICIAL") setBureauCode("PGRC");
                }}
                className="gov-input text-xs"
              >
                <option value="RB_OFFICIAL">RB Official (Regional)</option>
                <option value="PGRC_OFFICIAL">PGRC Official (Grievance)</option>
                <option value="SUPERVISOR">Supervisor (All Bureaus)</option>
                <option value="SYSTEM_ADMIN">System Administrator</option>
              </select>
            </div>

            <div>
              <label className="gov-label" htmlFor="uBureau">
                Bureau Jurisdiction
              </label>
              <select
                id="uBureau"
                value={bureauCode}
                disabled={role === "SUPERVISOR" || role === "SYSTEM_ADMIN"}
                onChange={(e) => setBureauCode(e.target.value)}
                className="gov-input text-xs disabled:opacity-50"
              >
                {bureausData?.map((b: any) => (
                  <option key={b.code} value={b.code}>
                    {b.code} - {b.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="gov-label" htmlFor="uDesig">
              Designation
            </label>
            <input
              id="uDesig"
              type="text"
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="Director / Deputy Director / Case Officer"
              className="gov-input text-xs"
            />
          </div>

          <div>
            <label className="gov-label" htmlFor="uPass">
              Initial Password <span className="text-red-500">*</span>
            </label>
            <input
              id="uPass"
              type="password"
              required
              value={initialPassword}
              onChange={(e) => setInitialPassword(e.target.value)}
              placeholder="Temporary secure password"
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* RESET PASSWORD MODAL */}
      <ConfirmModal
        isOpen={resetModalOpen}
        title={`Reset Password for ${selectedUser?.full_name}`}
        variant="warning"
        confirmLabel="Reset Password"
        isLoading={resetPasswordMutation.isPending}
        onConfirm={() => resetPasswordMutation.mutate()}
        onClose={() => setResetModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="rPass">
              New Password <span className="text-red-500">*</span>
            </label>
            <input
              id="rPass"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter new strong password"
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>
    </div>
  );
};
