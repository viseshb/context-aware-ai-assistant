import { Suspense } from "react";
import ApprovalForm from "@/components/admin/ApprovalForm";

export default function ApprovePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background text-text-muted">Loading...</div>}>
      <ApprovalForm />
    </Suspense>
  );
}
