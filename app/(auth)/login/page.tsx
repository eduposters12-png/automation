import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { LoginForm } from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <Link href="/" className="text-lg font-bold text-gray-950">ListifyAI</Link>
          <h1 className="mt-6 text-2xl font-bold text-gray-950">Login</h1>
          <p className="mt-2 text-sm text-gray-600">Access your Etsy listing workspace.</p>
        </div>
        <LoginForm />
        <p className="mt-5 text-sm text-gray-600">
          New to ListifyAI?{" "}
          <Link href="/register" className="font-semibold text-primary hover:text-indigo-500">
            Create account
          </Link>
        </p>
      </Card>
    </main>
  );
}
