"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";

interface ChatResponse {
  reply: string;
  provider: string;
  model: string;
}

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  model?: string;
}

const API_URL = "http://127.0.0.1:8010/api/chat";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const nextMessageId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = input.trim();

    if (!message || loading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: nextMessageId.current++,
      role: "user",
      content: message,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          provider: "mock",
        }),
        cache: "no-store",
      });

      const payload: unknown = await response.json();

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;

        if (
          typeof payload === "object" &&
          payload !== null &&
          "detail" in payload &&
          typeof payload.detail === "string"
        ) {
          errorMessage = payload.detail;
        }

        throw new Error(errorMessage);
      }

      const data = payload as ChatResponse;

      if (
        typeof data.reply !== "string" ||
        typeof data.provider !== "string" ||
        typeof data.model !== "string"
      ) {
        throw new Error("Invalid response received from the backend.");
      }

      const assistantMessage: ChatMessage = {
        id: nextMessageId.current++,
        role: "assistant",
        content: data.reply,
        model: `${data.provider} · ${data.model}`,
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to the backend.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col bg-[#080b14] text-white">
      <header className="flex h-20 shrink-0 items-center justify-between border-b border-white/[0.07] px-5 sm:px-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 text-lg font-bold"
            aria-label="AI UNIVERSE Dashboard"
          >
            AI
          </Link>

          <div>
            <h1 className="font-semibold">AI Chat</h1>
            <p className="text-xs text-slate-500">AI UNIVERSE Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/[0.07] px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span className="text-xs font-medium text-amber-300">Mock Mode</span>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 py-6 sm:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Conversation</h2>
            <p className="mt-1 text-xs text-slate-500">
              Connected to the AI UNIVERSE backend
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              setMessages([]);
              setError("");
              nextMessageId.current = 1;
            }}
            disabled={loading || messages.length === 0}
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear chat
          </button>
        </div>

        <div className="flex-1 space-y-5">
          {messages.length === 0 && (
            <div className="flex min-h-[45vh] flex-col items-center justify-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-2xl">
                ✦
              </div>

              <h3 className="mt-6 text-2xl font-semibold">
                Welcome to AI Chat
              </h3>

              <p className="mt-3 max-w-md text-sm leading-7 text-slate-400">
                Send your first message to test the connection between the AI
                UNIVERSE frontend and backend.
              </p>

              <div className="mt-6 rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 text-xs text-slate-500">
                Current provider:{" "}
                <span className="font-medium text-blue-300">Mock Provider</span>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <article
              key={message.id}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[90%] rounded-2xl p-4 sm:max-w-[80%] ${
                  message.role === "user"
                    ? "rounded-br-sm bg-blue-600 text-white"
                    : "rounded-bl-sm border border-white/[0.08] bg-[#111827] text-slate-200"
                }`}
              >
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider opacity-60">
                  {message.role === "user" ? "You" : "AI UNIVERSE"}
                </div>

                <p className="whitespace-pre-wrap text-sm leading-7">
                  {message.content}
                </p>

                {message.model && (
                  <div className="mt-3 border-t border-white/10 pt-2 text-[10px] text-slate-500">
                    {message.model}
                  </div>
                )}
              </div>
            </article>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm border border-white/[0.08] bg-[#111827] px-4 py-3 text-sm text-slate-400">
                Backend is processing your message...
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {error && (
          <div
            role="alert"
            className="mt-5 rounded-xl border border-red-500/20 bg-red-500/[0.07] p-4 text-sm text-red-300"
          >
            <p className="font-semibold">Connection error</p>
            <p className="mt-1 break-words">{error}</p>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="mt-6 rounded-2xl border border-white/[0.09] bg-[#101727] p-3 shadow-xl shadow-black/10"
        >
          <label htmlFor="chat-message" className="sr-only">
            Your message
          </label>

          <textarea
            id="chat-message"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Message AI UNIVERSE..."
            rows={3}
            maxLength={10000}
            disabled={loading}
            className="w-full resize-none bg-transparent px-3 py-2 text-sm leading-7 text-white outline-none placeholder:text-slate-600 disabled:opacity-50"
          />

          <div className="flex items-center justify-between border-t border-white/[0.07] pt-3">
            <span className="px-2 text-[10px] text-slate-600">
              Mock responses · No API key required
            </span>

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? "Sending..." : "Send message"}
            </button>
          </div>
        </form>

        <p className="mt-4 text-center text-[10px] text-slate-600">
          AI UNIVERSE Development Build · Mock Provider
        </p>
      </section>
    </main>
  );
}
