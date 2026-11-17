
"use client";

import { useEffect, useState } from "react";

interface HealthResponse {
  status: string;
  backend: string;
  message: string;
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8010/api/health",
          {
            signal: controller.signal,
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP Error: ${response.status}`);
        }

        const data: HealthResponse = await response.json();
        setHealth(data);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }

        setError(
          err instanceof Error ? err.message : "Connection failed"
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void checkBackend();

    return () => controller.abort();
  }, []);

  return (
    <main className="min-h-screen bg-[#080b14] text-white flex items-center justify-center p-6">
      <section className="w-full max-w-2xl rounded-2xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl">
        <div className="mb-8">
          <p className="text-sm tracking-[0.3em] text-blue-400">
            MULTI-AI COMMAND CENTER
          </p>

          <h1 className="mt-3 text-4xl font-bold">
            AI UNIVERSE
          </h1>

          <p className="mt-3 text-gray-400">
            Your unified artificial intelligence workspace.
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-black/20 p-5">
          <h2 className="text-lg font-semibold">
            Backend Connection
          </h2>

          {loading && (
            <p className="mt-4 text-yellow-400">
              Connecting to FastAPI...
            </p>
          )}

          {health && (
            <div className="mt-4 space-y-3">
              <p className="text-green-400 font-semibold">
                ● Backend Connected
              </p>

              <div className="text-sm text-gray-300 space-y-2">
                <p>Status: {health.status}</p>
                <p>Backend: {health.backend}</p>
                <p>Message: {health.message}</p>
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 text-red-400">
              Connection Error: {error}
            </p>
          )}
        </div>

        <p className="mt-8 text-center text-xs text-gray-500">
          AI UNIVERSE · Version 0.1.0 · Development
        </p>
      </section>
    </main>
  );
}
