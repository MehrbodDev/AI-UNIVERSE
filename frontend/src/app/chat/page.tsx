"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";

type ProviderLifecycleStatus =
  | "planned"
  | "disabled"
  | "policy_review_required"
  | "configuration_required"
  | "integration_unavailable"
  | "not_registered"
  | "ready";

interface CatalogProvider {
  id: string;
  name: string;
  company: string;
  status: string;
}

interface LifecycleProvider {
  provider_id: string;
  status: ProviderLifecycleStatus;
  enabled: boolean;
  registered: boolean;
  has_api_key: boolean;
  reason: string;
}

interface RegisteredProvider {
  name: string;
  model: string;
}

interface ProviderOption {
  id: string;
  name: string;
  company: string;
  status: ProviderLifecycleStatus;
  registered: boolean;
  model?: string;
  reason: string;
}

interface MultiChatError {
  code: string;
  message: string;
  retryable: boolean;
  retry_after: number | null;
}

interface MultiChatResult {
  provider: string;
  model: string | null;
  status: "success" | "error";
  reply: string | null;
  error: MultiChatError | null;
}

interface MultiChatResponse {
  results: MultiChatResult[];
  total: number;
  succeeded: number;
  failed: number;
}

interface ChatTurn {
  id: number;
  message: string;
  results: MultiChatResult[];
  total: number;
  succeeded: number;
  failed: number;
  loading: boolean;
  error?: string;
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8010/api"
).replace(/\/+$/, "");

const MAX_SELECTED_PROVIDERS = 5;
const MIN_SELECTED_PROVIDERS = 2;

const STATUS_LABELS: Record<ProviderLifecycleStatus, string> = {
  planned: "Planned",
  disabled: "Disabled",
  policy_review_required: "Policy review required",
  configuration_required: "Configuration required",
  integration_unavailable: "Integration unavailable",
  not_registered: "Not registered",
  ready: "Ready",
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isProviderLifecycleStatus(
  value: unknown,
): value is ProviderLifecycleStatus {
  return typeof value === "string" && Object.hasOwn(STATUS_LABELS, value);
}

function parseCatalogProviders(value: unknown): CatalogProvider[] {
  if (!isObject(value) || !Array.isArray(value.providers)) {
    throw new Error("Invalid provider catalog received.");
  }

  const providers: CatalogProvider[] = value.providers.map((item) => {
    if (
      !isObject(item) ||
      !isNonEmptyString(item.id) ||
      !isNonEmptyString(item.name) ||
      !isNonEmptyString(item.company) ||
      !isNonEmptyString(item.status)
    ) {
      throw new Error("Invalid provider catalog entry received.");
    }

    return {
      id: item.id,
      name: item.name,
      company: item.company,
      status: item.status,
    };
  });

  const providerIds = providers.map((provider) => provider.id);

  if (new Set(providerIds).size !== providerIds.length) {
    throw new Error("Duplicate provider IDs received in catalog.");
  }

  return providers;
}

function parseLifecycleProviders(value: unknown): LifecycleProvider[] {
  if (!isObject(value) || !Array.isArray(value.providers)) {
    throw new Error("Invalid provider lifecycle information received.");
  }

  const providers: LifecycleProvider[] = value.providers.map((item) => {
    if (
      !isObject(item) ||
      !isNonEmptyString(item.provider_id) ||
      !isProviderLifecycleStatus(item.status) ||
      typeof item.enabled !== "boolean" ||
      typeof item.registered !== "boolean" ||
      typeof item.has_api_key !== "boolean" ||
      typeof item.reason !== "string"
    ) {
      throw new Error("Invalid provider lifecycle entry received.");
    }

    return {
      provider_id: item.provider_id,
      status: item.status,
      enabled: item.enabled,
      registered: item.registered,
      has_api_key: item.has_api_key,
      reason: item.reason,
    };
  });

  const providerIds = providers.map((provider) => provider.provider_id);

  if (new Set(providerIds).size !== providerIds.length) {
    throw new Error("Duplicate provider IDs received in lifecycle data.");
  }

  return providers;
}

function parseRegisteredProviders(value: unknown): RegisteredProvider[] {
  if (!isObject(value) || !Array.isArray(value.providers)) {
    throw new Error("Invalid registered provider information received.");
  }

  const providers: RegisteredProvider[] = value.providers.map((item) => {
    if (
      !isObject(item) ||
      !isNonEmptyString(item.name) ||
      typeof item.model !== "string"
    ) {
      throw new Error("Invalid registered provider entry received.");
    }

    return {
      name: item.name,
      model: item.model,
    };
  });

  const providerNames = providers.map((provider) => provider.name);

  if (new Set(providerNames).size !== providerNames.length) {
    throw new Error("Duplicate registered provider names received.");
  }

  return providers;
}

function parseMultiChatResponse(
  value: unknown,
  expectedProviders: string[],
): MultiChatResponse {
  if (
    !isObject(value) ||
    !Array.isArray(value.results) ||
    !Number.isInteger(value.total) ||
    !Number.isInteger(value.succeeded) ||
    !Number.isInteger(value.failed)
  ) {
    throw new Error("Invalid multi-provider response received.");
  }

  const results: MultiChatResult[] = value.results.map((item) => {
    if (
      !isObject(item) ||
      !isNonEmptyString(item.provider) ||
      (item.status !== "success" && item.status !== "error")
    ) {
      throw new Error("Invalid provider result received.");
    }

    if (
      item.model !== null &&
      item.model !== undefined &&
      typeof item.model !== "string"
    ) {
      throw new Error("Invalid provider model received.");
    }

    if (
      item.reply !== null &&
      item.reply !== undefined &&
      typeof item.reply !== "string"
    ) {
      throw new Error("Invalid provider reply received.");
    }

    let error: MultiChatError | null = null;

    if (item.error !== null && item.error !== undefined) {
      if (
        !isObject(item.error) ||
        !isNonEmptyString(item.error.code) ||
        typeof item.error.message !== "string" ||
        typeof item.error.retryable !== "boolean" ||
        (item.error.retry_after !== null &&
          (typeof item.error.retry_after !== "number" ||
            !Number.isFinite(item.error.retry_after) ||
            item.error.retry_after < 0))
      ) {
        throw new Error("Invalid provider error received.");
      }

      error = {
        code: item.error.code,
        message: item.error.message,
        retryable: item.error.retryable,
        retry_after: item.error.retry_after,
      };
    }

    const reply = typeof item.reply === "string" ? item.reply : null;

    if (item.status === "success") {
      if (reply === null || error !== null) {
        throw new Error("Inconsistent successful provider result.");
      }
    }

    if (item.status === "error") {
      if (error === null || reply !== null) {
        throw new Error("Inconsistent failed provider result.");
      }
    }

    return {
      provider: item.provider,
      model: typeof item.model === "string" ? item.model : null,
      status: item.status,
      reply,
      error,
    };
  });

  const resultProviders = results.map((result) => result.provider);
  const uniqueResultProviders = new Set(resultProviders);

  if (uniqueResultProviders.size !== results.length) {
    throw new Error("Duplicate provider results received.");
  }

  if (
    results.length !== expectedProviders.length ||
    expectedProviders.some((provider) => !uniqueResultProviders.has(provider))
  ) {
    throw new Error("Provider results do not match the original request.");
  }

  const succeeded = results.filter(
    (result) => result.status === "success",
  ).length;

  const failed = results.length - succeeded;

  if (
    value.total !== results.length ||
    value.succeeded !== succeeded ||
    value.failed !== failed
  ) {
    throw new Error("Provider response statistics are inconsistent.");
  }

  return {
    results,
    total: results.length,
    succeeded,
    failed,
  };
}

function getStatusColor(status: ProviderLifecycleStatus): string {
  if (status === "ready") {
    return "border-emerald-400/20 bg-emerald-400/10 text-emerald-300";
  }

  if (status === "planned") {
    return "border-amber-400/20 bg-amber-400/10 text-amber-300";
  }

  return "border-red-400/20 bg-red-400/10 text-red-300";
}

export default function ChatPage() {
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [providersLoading, setProvidersLoading] = useState(true);
  const [providersError, setProvidersError] = useState("");

  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectionNotice, setSelectionNotice] = useState("");

  const nextTurnId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadProviders() {
      setProvidersLoading(true);
      setProvidersError("");

      try {
        const [catalogResponse, lifecycleResponse, registeredResponse] =
          await Promise.all([
            fetch(`${API_BASE_URL}/providers/catalog`, {
              cache: "no-store",
              signal: controller.signal,
            }),
            fetch(`${API_BASE_URL}/providers/lifecycle`, {
              cache: "no-store",
              signal: controller.signal,
            }),
            fetch(`${API_BASE_URL}/providers`, {
              cache: "no-store",
              signal: controller.signal,
            }),
          ]);

        if (controller.signal.aborted) {
          return;
        }

        if (
          !catalogResponse.ok ||
          !lifecycleResponse.ok ||
          !registeredResponse.ok
        ) {
          throw new Error("Unable to load provider information.");
        }

        const [catalogData, lifecycleData, registeredData] = await Promise.all([
          catalogResponse.json(),
          lifecycleResponse.json(),
          registeredResponse.json(),
        ]);

        if (controller.signal.aborted) {
          return;
        }

        const catalog = parseCatalogProviders(catalogData);
        const lifecycle = parseLifecycleProviders(lifecycleData);
        const registered = parseRegisteredProviders(registeredData);

        const lifecycleMap = new Map(
          lifecycle.map((item) => [item.provider_id, item]),
        );

        const registeredMap = new Map(
          registered.map((item) => [item.name, item]),
        );

        const options: ProviderOption[] = catalog.map((provider) => {
          const lifecycleInfo = lifecycleMap.get(provider.id);
          const registeredInfo = registeredMap.get(provider.id);

          return {
            id: provider.id,
            name: provider.name,
            company: provider.company,
            status: lifecycleInfo?.status ?? "planned",
            registered:
              registeredInfo !== undefined ||
              lifecycleInfo?.registered === true,
            model: registeredInfo?.model,
            reason:
              lifecycleInfo?.reason ??
              "Provider lifecycle information is unavailable.",
          };
        });

        for (const provider of registered) {
          if (!options.some((item) => item.id === provider.name)) {
            options.push({
              id: provider.name,
              name: provider.name === "mock" ? "Mock Provider" : provider.name,
              company: provider.name === "mock" ? "AI UNIVERSE" : provider.name,
              status: "ready",
              registered: true,
              model: provider.model,
              reason: "Provider is currently registered.",
            });
          }
        }

        options.sort((a, b) => {
          if (a.id === "mock") return -1;
          if (b.id === "mock") return 1;

          if (a.registered !== b.registered) {
            return a.registered ? -1 : 1;
          }

          return a.name.localeCompare(b.name);
        });

        if (controller.signal.aborted) {
          return;
        }

        setProviders(options);

        const mockProvider = options.find((provider) => provider.id === "mock");

        const otherProvider = options.find(
          (provider) => provider.id !== "mock",
        );

        const initialSelection = [
          ...(mockProvider ? [mockProvider.id] : []),
          ...(otherProvider ? [otherProvider.id] : []),
        ];

        setSelectedProviders(
          initialSelection.length > 0
            ? initialSelection
            : options
                .slice(0, MIN_SELECTED_PROVIDERS)
                .map((provider) => provider.id),
        );
      } catch (error) {
        if (
          controller.signal.aborted ||
          (error instanceof Error && error.name === "AbortError")
        ) {
          return;
        }

        setProvidersError(
          error instanceof Error ? error.message : "Unable to load providers.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setProvidersLoading(false);
        }
      }
    }

    void loadProviders();

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [turns, loading]);

  function toggleProvider(providerId: string) {
    if (loading) {
      return;
    }

    setSelectionNotice("");

    if (selectedProviders.includes(providerId)) {
      if (selectedProviders.length <= MIN_SELECTED_PROVIDERS) {
        setSelectionNotice("At least two providers must be selected.");
        return;
      }

      setSelectedProviders((current) =>
        current.filter((item) => item !== providerId),
      );

      return;
    }

    if (selectedProviders.length >= MAX_SELECTED_PROVIDERS) {
      setSelectionNotice("You can select a maximum of five providers.");
      return;
    }

    setSelectedProviders((current) => [...current, providerId]);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = input.trim();
    const providersToQuery = [...selectedProviders];

    if (
      !message ||
      loading ||
      providersToQuery.length < MIN_SELECTED_PROVIDERS ||
      providersToQuery.length > MAX_SELECTED_PROVIDERS
    ) {
      return;
    }

    const turnId = nextTurnId.current++;

    const pendingTurn: ChatTurn = {
      id: turnId,
      message,
      results: [],
      total: providersToQuery.length,
      succeeded: 0,
      failed: 0,
      loading: true,
    };

    setTurns((current) => [...current, pendingTurn]);
    setInput("");
    setLoading(true);
    setSelectionNotice("");

    try {
      const response = await fetch(`${API_BASE_URL}/chat/multi`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          providers: providersToQuery,
        }),
        cache: "no-store",
      });

      let payload: unknown = null;

      try {
        payload = await response.json();
      } catch {
        // The response may not contain valid JSON.
      }

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;

        if (isObject(payload) && typeof payload.detail === "string") {
          errorMessage = payload.detail;
        }

        throw new Error(errorMessage);
      }

      const data = parseMultiChatResponse(payload, providersToQuery);

      setTurns((current) =>
        current.map((turn) =>
          turn.id === turnId
            ? {
                ...turn,
                results: data.results,
                total: data.total,
                succeeded: data.succeeded,
                failed: data.failed,
                loading: false,
              }
            : turn,
        ),
      );
    } catch (error) {
      setTurns((current) =>
        current.map((turn) =>
          turn.id === turnId
            ? {
                ...turn,
                loading: false,
                error:
                  error instanceof Error
                    ? error.message
                    : "Unable to connect to the backend.",
              }
            : turn,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    if (loading) {
      return;
    }

    setTurns([]);
    nextTurnId.current = 1;
  }

  const registeredCount = providers.filter(
    (provider) => provider.registered,
  ).length;

  const selectedUnavailable = providers.filter(
    (provider) =>
      selectedProviders.includes(provider.id) &&
      (!provider.registered || provider.status !== "ready"),
  );

  return (
    <main className="flex min-h-screen flex-col bg-[#080b14] text-white">
      <header className="flex min-h-20 shrink-0 items-center justify-between border-b border-white/[0.07] px-5 py-4 sm:px-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-3 rounded-lg outline-none transition hover:opacity-80 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 text-lg font-bold">
              AI
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide">AI UNIVERSE</h1>
              <p className="text-[10px] text-slate-500">
                Multi-AI Command Center
              </p>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/[0.07] px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span className="text-xs font-medium text-amber-300">
            Multi-provider Test
          </span>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-6 sm:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Multi-model Conversation</h2>
            <p className="mt-1 text-xs text-slate-500">
              Send one message to multiple providers concurrently.
            </p>
          </div>

          <button
            type="button"
            onClick={clearChat}
            disabled={loading || turns.length === 0}
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear chat
          </button>
        </div>

        <section className="mb-6 rounded-2xl border border-white/[0.08] bg-[#101727] p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Provider selection</h3>
              <p className="mt-1 text-xs text-slate-500">
                Select 2 to 5 providers for each request.
              </p>
            </div>

            <span className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-400">
              {selectedProviders.length}/5 selected
            </span>
          </div>

          {providersLoading && (
            <p className="text-sm text-slate-400">
              Loading provider information...
            </p>
          )}

          {providersError && (
            <div
              role="alert"
              className="rounded-xl border border-red-500/20 bg-red-500/[0.07] p-3 text-sm text-red-300"
            >
              {providersError}
            </div>
          )}

          {!providersLoading && !providersError && (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {providers.map((provider) => {
                  const selected = selectedProviders.includes(provider.id);

                  return (
                    <button
                      key={provider.id}
                      type="button"
                      onClick={() => toggleProvider(provider.id)}
                      disabled={loading}
                      aria-pressed={selected}
                      className={`rounded-xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                        selected
                          ? "border-blue-500/60 bg-blue-500/[0.09]"
                          : "border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.05]"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold">
                            {provider.name}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {provider.company}
                          </p>
                        </div>

                        <span
                          className={`rounded-full border px-2 py-1 text-[9px] ${
                            selected
                              ? "border-blue-400/30 bg-blue-400/10 text-blue-300"
                              : "border-white/10 text-slate-500"
                          }`}
                        >
                          {selected ? "Selected" : "Select"}
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-1 text-[9px] ${getStatusColor(
                            provider.status,
                          )}`}
                        >
                          {STATUS_LABELS[provider.status]}
                        </span>

                        {provider.registered && (
                          <span className="text-[9px] text-emerald-300">
                            Registered
                          </span>
                        )}
                      </div>

                      {provider.model && (
                        <p className="mt-2 truncate text-[10px] text-slate-500">
                          Model: {provider.model}
                        </p>
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="mt-4 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-slate-400">
                    Registered providers
                  </span>
                  <span className="text-xs font-semibold text-white">
                    {registeredCount} / {providers.length}
                  </span>
                </div>

                <p className="mt-2 text-xs leading-6 text-slate-500">
                  Providers that are not registered can be selected to test
                  request orchestration and error isolation. They will not
                  generate real AI responses.
                </p>
              </div>

              {selectedUnavailable.length > 0 && (
                <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3 text-xs leading-6 text-amber-200">
                  Some selected providers are not currently ready:
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {selectedUnavailable.map((provider) => (
                      <li key={provider.id}>
                        <span className="font-semibold">{provider.name}</span>
                        {" — "}
                        {provider.reason}
                      </li>
                    ))}
                  </ul>
                  Their requests may return availability errors.
                </div>
              )}

              {selectionNotice && (
                <p role="alert" className="mt-3 text-xs text-amber-300">
                  {selectionNotice}
                </p>
              )}
            </>
          )}
        </section>

        <section className="flex-1 space-y-6">
          {turns.length === 0 && (
            <div className="flex min-h-[30vh] flex-col items-center justify-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-2xl">
                ✦
              </div>

              <h3 className="mt-6 text-2xl font-semibold">
                Multi-model Workspace
              </h3>

              <p className="mt-3 max-w-md text-sm leading-7 text-slate-400">
                Write a message and compare the independent results returned by
                the selected providers.
              </p>
            </div>
          )}

          {turns.map((turn) => (
            <article key={turn.id} className="space-y-4">
              <div className="flex justify-end">
                <div className="max-w-[90%] rounded-2xl rounded-br-sm bg-blue-600 p-4 sm:max-w-[75%]">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-blue-100/70">
                    You
                  </p>

                  <p className="whitespace-pre-wrap text-sm leading-7">
                    {turn.message}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-200">
                  Provider results
                </h3>

                {!turn.loading && !turn.error && (
                  <div className="flex gap-3 text-[10px]">
                    <span className="text-emerald-300">
                      {turn.succeeded} successful
                    </span>
                    <span className="text-red-300">{turn.failed} failed</span>
                  </div>
                )}
              </div>

              {turn.loading && (
                <div className="rounded-xl border border-white/[0.08] bg-[#111827] p-4 text-sm text-slate-400">
                  Waiting for independent provider results...
                </div>
              )}

              {turn.error && (
                <div
                  role="alert"
                  className="rounded-xl border border-red-500/20 bg-red-500/[0.07] p-4 text-sm text-red-300"
                >
                  <p className="font-semibold">Multi-provider request failed</p>
                  <p className="mt-2 break-words">{turn.error}</p>
                </div>
              )}

              {turn.results.length > 0 && (
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {turn.results.map((result, index) => (
                    <div
                      key={`${turn.id}-${result.provider}-${index}`}
                      className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#111827]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3">
                        <div>
                          <p className="text-sm font-semibold">
                            {result.provider}
                          </p>

                          <p className="mt-1 text-[10px] text-slate-500">
                            {result.model ?? "Model unavailable"}
                          </p>
                        </div>

                        <span
                          className={`rounded-full border px-2.5 py-1 text-[10px] ${
                            result.status === "success"
                              ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                              : "border-red-400/20 bg-red-400/10 text-red-300"
                          }`}
                        >
                          {result.status === "success" ? "Success" : "Error"}
                        </span>
                      </div>

                      <div className="p-4">
                        {result.status === "success" ? (
                          <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-200">
                            {result.reply}
                          </p>
                        ) : (
                          <div className="space-y-2">
                            <p className="text-sm font-medium text-red-300">
                              {result.error?.message ??
                                "Provider request failed."}
                            </p>

                            <p className="text-[10px] text-slate-500">
                              Error code: {result.error?.code ?? "unknown"}
                            </p>

                            {result.error?.retryable && (
                              <p className="text-[10px] text-amber-300">
                                This error may be temporary.
                              </p>
                            )}

                            {result.error?.retry_after !== null &&
                              result.error?.retry_after !== undefined && (
                                <p className="text-[10px] text-slate-500">
                                  Retry after: {result.error.retry_after}{" "}
                                  seconds
                                </p>
                              )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}

          <div ref={bottomRef} />
        </section>

        <form
          onSubmit={handleSubmit}
          className="mt-6 rounded-2xl border border-white/[0.08] bg-[#111827] p-4"
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Message AI UNIVERSE..."
            rows={3}
            maxLength={10000}
            disabled={loading || providersLoading || !!providersError}
            className="w-full resize-none bg-transparent px-3 py-2 text-sm leading-7 text-white outline-none placeholder:text-slate-600 disabled:opacity-50"
          />

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] pt-3">
            <span className="px-2 text-[10px] text-slate-500">
              {selectedProviders.length} providers selected · Maximum 5
            </span>

            <button
              type="submit"
              disabled={
                loading ||
                providersLoading ||
                !!providersError ||
                selectedProviders.length < MIN_SELECTED_PROVIDERS ||
                selectedProviders.length > MAX_SELECTED_PROVIDERS ||
                !input.trim()
              }
              className="rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? "Processing..." : "Send to selected providers"}
            </button>
          </div>
        </form>

        <p className="mt-4 text-center text-[10px] text-slate-600">
          AI UNIVERSE Development Build · Multi-provider orchestration
        </p>
      </section>
    </main>
  );
}
