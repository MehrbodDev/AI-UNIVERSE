"use client";

import { useEffect, useState } from "react";

interface HealthResponse {
  status: string;
  backend: string;
  message: string;
}

const modules = [
  {
    name: "AI Chat",
    description: "AI chat interface prototype; live provider integrations are not connected",
    icon: "message",
    iconClasses: "bg-blue-500/10 text-blue-300",
    status: "Prototype",
    href: "#ai-chat",
  },
  {
    name: "AI Arena",
    description: "Compare multiple AI models",
    icon: "arena",
    iconClasses: "bg-purple-500/10 text-purple-300",
    status: "Coming soon",
    href: "#ai-arena",
  },
  {
    name: "Research Lab",
    description: "Explore ideas and research",
    icon: "search",
    iconClasses: "bg-cyan-500/10 text-cyan-300",
    status: "Planned",
    href: "#research",
  },
  {
    name: "AI Classroom",
    description: "Learn with artificial intelligence",
    icon: "book",
    iconClasses: "bg-orange-500/10 text-orange-300",
    status: "Planned",
    href: "#classroom",
  },
  {
    name: "Code Studio",
    description: "Your AI programming workspace",
    icon: "code",
    iconClasses: "bg-green-500/10 text-green-300",
    status: "Planned",
    href: "#code-studio",
  },
  {
    name: "Knowledge Base",
    description: "Organize your knowledge",
    icon: "database",
    iconClasses: "bg-pink-500/10 text-pink-300",
    status: "Planned",
    href: "#knowledge",
  },
  {
    name: "Creative Studio",
    description: "Explore creative AI workflows",
    icon: "spark",
    iconClasses: "bg-yellow-500/10 text-yellow-300",
    status: "Planned",
    href: "#creative",
  },
  {
    name: "AI Agents",
    description: "Manage intelligent agents",
    icon: "bot",
    iconClasses: "bg-indigo-500/10 text-indigo-300",
    status: "Planned",
    href: "#agents",
  },
];

const navigation = [
  { name: "Dashboard", icon: "grid", href: "#dashboard" },
  { name: "AI Chat", icon: "message", href: "#ai-chat" },
  { name: "AI Arena", icon: "arena", href: "#ai-arena" },
  { name: "Research Lab", icon: "search", href: "#research" },
  { name: "AI Classroom", icon: "book", href: "#classroom" },
  { name: "Code Studio", icon: "code", href: "#code-studio" },
  { name: "Knowledge Base", icon: "database", href: "#knowledge" },
  { name: "AI Agents", icon: "bot", href: "#agents" },
];

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    grid: "M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z",
    message:
      "M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8z",
    arena: "M12 3v18 M3 12h18 M5 5l14 14 M19 5 5 19",
    search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.35-4.35",
    book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
    code: "m16 18 6-6-6-6 M8 6l-6 6 6 6 M14 4l-4 16",
    database:
      "M12 8c4.97 0 9-1.34 9-3s-4.03-3-9-3-9 1.34-9 3 4.03 3 9 3z M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5 M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3",
    spark:
      "m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3z M19 14l1.2 2.8L23 18l-2.8 1.2L19 22l-1.2-2.8L15 18l2.8-1.2L19 14z",
    bot: "M12 8V4H8 M12 4h4 M8 12h.01 M16 12h.01 M9 16h6 M5 8h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2z",
    settings:
      "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.5 2.6-.2-.1a1.7 1.7 0 0 0-1.8.2l-.2.1h-3l-.1-.2a1.7 1.7 0 0 0-1.5-1l-.2.1-2.6-1.5.1-.2a1.7 1.7 0 0 0-.2-1.8l-.1-.2v-3l.2-.1a1.7 1.7 0 0 0 1-1.5l-.1-.2 1.5-2.6.2.1a1.7 1.7 0 0 0 1.8-.2l.2-.1h3l.1.2a1.7 1.7 0 0 0 1.5 1l.2-.1 2.6 1.5-.1.2a1.7 1.7 0 0 0 .2 1.8l.1.2v3z",
    cpu: "M12 8v8 M8 12h8 M4 4h16v16H4z M9 1v3 M15 1v3 M9 20v3 M15 20v3 M1 9h3 M1 15h3 M20 9h3 M20 15h3",
    arrow: "M7 17 17 7 M7 7h10v10",
    clock: "M12 8v4l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.spark} />
    </svg>
  );
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkKey, setCheckKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      setLoading(true);
      setError("");
      setHealth(null);

      try {
        const response = await fetch("http://127.0.0.1:8010/api/health", {
          signal: controller.signal,
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`HTTP Error: ${response.status}`);
        }

        const data: HealthResponse = await response.json();
        setHealth(data);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }

        setError(err instanceof Error ? err.message : "Connection failed");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void checkBackend();

    return () => controller.abort();
  }, [checkKey]);

  const backendOnline = Boolean(health);

  return (
    <main id="dashboard" className="min-h-screen bg-[#080b14] text-white">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="hidden w-64 shrink-0 border-r border-white/[0.07] bg-[#0b1020] lg:flex lg:flex-col">
          <div className="flex h-20 items-center gap-3 border-b border-white/[0.07] px-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/20">
              <Icon name="spark" size={23} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-wide">AI UNIVERSE</h1>
              <p className="text-[10px] tracking-[0.25em] text-slate-500">
                COMMAND CENTER
              </p>
            </div>
          </div>

          <div className="px-4 pt-7">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Workspace
            </p>

            <nav className="space-y-1">
              {navigation.map((item, index) => (
                <a
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${
                    index === 0
                      ? "bg-blue-500/15 font-semibold text-blue-300"
                      : "text-slate-400 hover:bg-white/[0.05] hover:text-white"
                  }`}
                >
                  <Icon name={item.icon} size={18} />
                  {item.name}
                  {index === 0 && (
                    <span className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-400" />
                  )}
                </a>
              ))}
            </nav>
          </div>

          <div className="mt-auto p-4">
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                <Icon name="cpu" size={17} />
                System Status
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">FastAPI</span>
                <span
                  className={
                    backendOnline
                      ? "text-emerald-400"
                      : loading
                        ? "text-yellow-400"
                        : "text-red-400"
                  }
                >
                  {backendOnline ? "Online" : loading ? "Checking" : "Offline"}
                </span>
              </div>

              <div className="mt-3 flex items-center justify-between text-xs">
                <span className="text-slate-400">AI providers</span>
                <span className="text-slate-500">Not connected</span>
              </div>
            </div>

            <a
              href="#settings"
              className="mt-4 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-400 hover:bg-white/[0.05] hover:text-white"
            >
              <Icon name="settings" size={18} />
              Settings
            </a>

            <p className="mt-4 px-3 text-[10px] text-slate-600">
              AI UNIVERSE · Development build
            </p>
          </div>
        </aside>

        {/* Main Content */}
        <section className="min-w-0 flex-1">
          {/* Topbar */}
          <header className="flex h-20 items-center justify-between border-b border-white/[0.07] px-5 sm:px-8">
            <div>
              <p className="text-xs text-slate-500">Workspace / Overview</p>
              <h2 className="mt-1 text-lg font-semibold">Dashboard</h2>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs sm:flex">
                <span
                  className={`h-2 w-2 rounded-full ${
                    backendOnline
                      ? "bg-emerald-400"
                      : loading
                        ? "bg-yellow-400"
                        : "bg-red-400"
                  }`}
                />
                <span className="text-slate-300">
                  {backendOnline
                    ? "System Online"
                    : loading
                      ? "Connecting..."
                      : "Connection Error"}
                </span>
              </div>

              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-blue-400/20 bg-blue-500/10 text-sm font-bold text-blue-300">
                AI
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-7xl space-y-9 p-5 sm:p-8">
            {/* Welcome */}
            <section className="relative overflow-hidden rounded-3xl border border-blue-400/10 bg-gradient-to-br from-[#14254a] via-[#111a35] to-[#17112f] p-7 sm:p-10">
              <div className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-blue-500/15 blur-3xl" />
              <div className="pointer-events-none absolute -bottom-28 right-1/3 h-64 w-64 rounded-full bg-violet-500/15 blur-3xl" />

              <div className="relative max-w-2xl">
                <span className="inline-flex items-center gap-2 rounded-full border border-blue-300/20 bg-blue-300/10 px-3 py-1.5 text-[10px] font-semibold tracking-[0.15em] text-blue-200">
                  <Icon name="spark" size={13} />
                  MULTI-AI COMMAND CENTER
                </span>

                <h1 className="mt-6 text-3xl font-bold leading-tight sm:text-5xl">
                  Welcome to{" "}
                  <span className="bg-gradient-to-r from-blue-300 to-violet-300 bg-clip-text text-transparent">
                    AI UNIVERSE
                  </span>
                </h1>

                <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300 sm:text-base">
                  Your unified workspace for artificial intelligence. Discover
                  models, explore ideas, build projects and manage your AI tools
                  in one place.
                </p>

                <a
                  href="#modules"
                  className="mt-7 inline-flex items-center gap-2 rounded-xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-400"
                >
                  Explore Workspace
                  <Icon name="arrow" size={16} />
                </a>
              </div>
            </section>

            {/* System Overview */}
            <section>
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">System Overview</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Current infrastructure status
                  </p>
                </div>

                <button
                  onClick={() => setCheckKey((value) => value + 1)}
                  disabled={loading}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 transition hover:bg-white/[0.06] disabled:opacity-50"
                >
                  {loading ? "Checking..." : "Refresh Status"}
                </button>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-2xl border border-white/[0.07] bg-[#101727] p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Backend API</span>
                    <Icon name="cpu" size={20} />
                  </div>

                  <p
                    className={`mt-4 text-2xl font-bold ${backendOnline ? "text-emerald-400" : "text-slate-300"}`}
                  >
                    {backendOnline
                      ? "Online"
                      : loading
                        ? "Checking..."
                        : "Offline"}
                  </p>

                  <p className="mt-2 text-xs text-slate-500">
                    FastAPI · Port 8010
                  </p>
                </div>

                <div className="rounded-2xl border border-white/[0.07] bg-[#101727] p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">AI Provider</span>
                    <Icon name="bot" size={20} />
                  </div>

                  <p className="mt-4 text-2xl font-bold text-blue-300">
                    Not connected
                  </p>

                  <p className="mt-2 text-xs text-slate-500">
                    11 providers planned · integrations unverified
                  </p>
                </div>

                <div className="rounded-2xl border border-white/[0.07] bg-[#101727] p-5 sm:col-span-2 xl:col-span-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Platform</span>
                    <Icon name="grid" size={20} />
                  </div>

                  <p className="mt-4 text-2xl font-bold text-violet-300">
                    Development
                  </p>

                  <p className="mt-2 text-xs text-slate-500">
                    Frontend + Backend
                  </p>
                </div>
              </div>

              {error && (
                <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300">
                  Backend connection error: {error}
                </div>
              )}

              {health && (
                <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-xs text-emerald-300">
                  {health.message}
                </div>
              )}
            </section>

            {/* Modules */}
            <section id="modules">
              <div className="mb-5">
                <h2 className="text-lg font-semibold">AI Workspace</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Explore the modules of your AI ecosystem
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {modules.map((module) => (
                  <a
                    key={module.name}
                    id={module.href.replace("#", "")}
                    href={module.href}
                    className="group rounded-2xl border border-white/[0.07] bg-[#101727] p-5 transition duration-200 hover:-translate-y-1 hover:border-blue-400/30 hover:bg-[#141e32]"
                  >
                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-xl ${module.iconClasses}`}
                    >
                      <Icon name={module.icon} size={22} />
                    </div>

                    <h3 className="mt-5 font-semibold transition group-hover:text-blue-300">
                      {module.name}
                    </h3>

                    <p className="mt-2 min-h-10 text-xs leading-5 text-slate-500">
                      {module.description}
                    </p>

                    <div className="mt-5 flex items-center justify-between">
                      <span className="text-[10px] text-slate-500">
                        {module.status}
                      </span>
                      <Icon name="arrow" size={15} />
                    </div>
                  </a>
                ))}
              </div>
            </section>

            {/* Roadmap */}
            <section
              id="roadmap"
              className="rounded-2xl border border-white/[0.07] bg-[#101727] p-6"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300">
                  <Icon name="clock" size={21} />
                </div>
                <div>
                  <h2 className="font-semibold">Development Roadmap</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Current project milestones
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                {[
                  ["Project foundation", true],
                  ["Frontend and backend setup", true],
                  ["GitHub repository", true],
                  ["Dashboard interface", true],
                  ["Provider catalog and metadata", true],
                  ["Functional AI Chat", false],
                  ["Multi-model AI Arena", false],
                ].map(([name, done]) => (
                  <div key={String(name)} className="flex items-center gap-3">
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                        done
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "border border-white/15 text-slate-600"
                      }`}
                    >
                      {done ? "✓" : " "}
                    </span>
                    <span
                      className={`text-sm ${done ? "text-slate-300" : "text-slate-500"}`}
                    >
                      {String(name)}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <footer className="border-t border-white/[0.07] py-6 text-center text-xs text-slate-600">
              AI UNIVERSE · Multi-AI Command Center · Built for the future
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}
