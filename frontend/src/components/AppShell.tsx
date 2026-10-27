import React from "react";
import { Outlet } from "react-router-dom";
import { TopBar, Sidebar } from "./Navigation";

export const AppShell: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-surface-bg text-surface-text">
      {/* Top Header */}
      <TopBar />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 flex flex-col">
          <div className="flex-1 max-w-7xl w-full mx-auto">
            <Outlet />
          </div>

          {/* Mandatory Prototype Footer Banner */}
          <footer className="mt-8 pt-4 border-t border-surface-border text-center text-xs text-surface-subtle">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-surface-muted border border-surface-border font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              Prototype - synthetic data only
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};
