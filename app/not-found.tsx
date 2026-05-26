import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-950">Page not found</h1>
        <Link href="/dashboard" className="mt-5 inline-flex min-h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600">
          Go to Dashboard
        </Link>
      </div>
    </main>
  );
}
