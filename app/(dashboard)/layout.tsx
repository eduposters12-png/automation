import { redirect } from "next/navigation";

import { CreditAlertWrapper } from "@/components/CreditAlertWrapper";
import { Sidebar } from "@/components/Sidebar";
import { getCurrentUser } from "@/lib/server-api";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const auth = await getCurrentUser();

  if (!auth) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50 lg:flex">
      <Sidebar user={auth.user} />
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
        {children}
        <CreditAlertWrapper />
      </main>
    </div>
  );
}
