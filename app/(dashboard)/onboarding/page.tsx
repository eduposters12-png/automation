import { OnboardingSteps } from "@/components/OnboardingSteps";
import { getOnboardingStatus } from "@/lib/server-api";

export default async function OnboardingPage({
  searchParams
}: {
  searchParams?: { etsy?: string };
}) {
  const status = await getOnboardingStatus();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Onboarding</h1>
        <p className="mt-1 text-sm text-gray-600">Connect Etsy OAuth and add Claude to unlock listing jobs.</p>
      </div>
      <OnboardingSteps
        initialStatus={status || { etsy_connected: false, claude_key_added: false, complete: false }}
        etsyResult={searchParams?.etsy}
      />
    </div>
  );
}
