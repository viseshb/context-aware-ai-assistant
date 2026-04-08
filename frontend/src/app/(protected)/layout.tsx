import type { ReactNode } from "react";
import ProtectedSidebar from "@/components/layout/ProtectedSidebar";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex h-screen">
        <ProtectedSidebar />
        <main className="min-w-0 flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}
