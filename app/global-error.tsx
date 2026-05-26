"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body>
        <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-950">Something went wrong</h1>
            <button
              type="button"
              className="mt-5 min-h-10 rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600"
              onClick={reset}
            >
              Reload page
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
