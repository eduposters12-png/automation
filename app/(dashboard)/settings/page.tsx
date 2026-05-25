import { SettingsForm } from "@/components/SettingsForm";
import { getSettings } from "@/lib/server-api";

export default async function SettingsPage() {
  const settings = await getSettings();

  if (!settings) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Settings</h1>
        <p className="mt-1 text-sm text-gray-600">Manage shop details, Claude access, and Etsy OAuth.</p>
      </div>
      <SettingsForm initialSettings={settings} />
    </div>
  );
}
