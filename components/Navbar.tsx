import Link from "next/link";

export function Navbar() {
  return (
    <header className="border-b border-gray-100 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="text-lg font-bold tracking-tight text-gray-950">
          ListifyAI
        </Link>
        <nav className="flex items-center gap-2">
          <Link href="/login" className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-950">
            Login
          </Link>
          <Link
            href="/register"
            className="hidden min-h-10 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 sm:inline-flex"
          >
            Start free
          </Link>
        </nav>
      </div>
    </header>
  );
}
