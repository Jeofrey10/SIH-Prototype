import React from "react";
import { Link } from "react-router-dom";
import { ShieldX, Home } from "lucide-react";

export const UnauthorizedPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-surface-bg flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-4">
        <ShieldX className="w-8 h-8" />
      </div>
      <h1 className="text-2xl font-bold text-surface-text">Access Denied (403)</h1>
      <p className="text-sm text-surface-subtle max-w-md mt-2 mb-6">
        You do not possess the required official role or administrative clearance to view
        this section of the grievance portal.
      </p>
      <Link
        to="/dashboard"
        className="gov-btn-primary text-sm py-2 px-5 flex items-center gap-2"
      >
        <Home className="w-4 h-4" />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
};

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-surface-bg flex flex-col items-center justify-center p-6 text-center">
      <h1 className="text-5xl font-black text-brand-900">404</h1>
      <h2 className="text-xl font-bold text-surface-text mt-2">Page Not Found</h2>
      <p className="text-sm text-surface-subtle max-w-md mt-1 mb-6">
        The requested portal endpoint or document does not exist or has been moved.
      </p>
      <Link
        to="/dashboard"
        className="gov-btn-primary text-sm py-2 px-5 flex items-center gap-2"
      >
        <Home className="w-4 h-4" />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
};
