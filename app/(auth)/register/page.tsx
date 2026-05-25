import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { RegisterForm } from "@/components/RegisterForm";

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <Link href="/" className="text-lg font-bold text-gray-950">ListifyAI</Link>
          <h1 className="mt-6 text-2xl font-bold text-gray-950">Create Account</h1>
          <p className="mt-2 text-sm text-gray-600">Set up your Etsy AI operations workspace.</p>
        </div>
        <RegisterForm />
        <p className="mt-5 text-sm text-gray-600">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-primary hover:text-indigo-500">
            Login
          </Link>
        </p>
      </Card>
    </main>
  );
}
