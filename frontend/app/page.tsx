"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Composer from "./components/Composer";
import HomeHero from "./components/HomeHero";
import Sidebar from "./components/Sidebar";
import UniCard from "./components/UniversityCard";
import {
  api,
  type ChatMessage,
  type ChatSummary,
  type Payload,
  type UniversityCard,
} from "@/lib/api";

type View = "home" | "chat";

export default function Page() {
  const [view, setView] = useState<View>("home");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [extraCards, setExtraCards] = useState<UniversityCard[]>([]);
  const scroller = useRef<HTMLDivElement>(null);

  const lastPayload: Payload | undefined = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].payload) return messages[i].payload;
    }
    return undefined;
  }, [messages]);

  async function refreshChats() {
    const data = await api<{ chats: ChatSummary[] }>("/api/chats");
    setChats(data.chats);
  }

  useEffect(() => {
    refreshChats().catch(() => {});
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string, existingSession?: string | null) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setInput("");
    setView("chat");
    setExtraCards([]);
    setMessages((m) => [...m, { role: "user", content: trimmed }]);
    setLoading(true);
    try {
      const data = await api<Payload & { session_id: string; messages: ChatMessage[] }>(
        "/api/chat",
        {
          method: "POST",
          body: JSON.stringify({ message: trimmed, session_id: existingSession ?? sessionId }),
        },
      );
      setSessionId(data.session_id);
      setMessages((data.messages as ChatMessage[]) || [
        { role: "user", content: trimmed },
        { role: "assistant", content: data.narration || data.clarification || "", payload: data },
      ]);
      await refreshChats();
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "The planner could not answer just then.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function onNew() {
    const created = await api<{ session_id: string }>("/api/chats", { method: "POST" });
    setSessionId(created.session_id);
    setMessages([]);
    setExtraCards([]);
    setView("home");
    await refreshChats();
  }

  async function onSelect(id: string) {
    const chat = await api<{ session_id: string; messages: ChatMessage[] }>(`/api/chats/${id}`);
    setSessionId(id);
    setMessages(chat.messages || []);
    setExtraCards([]);
    setView(chat.messages?.length ? "chat" : "home");
  }

  async function onDelete(id: string) {
    await api(`/api/chats/${id}`, { method: "DELETE" });
    if (sessionId === id) {
      setSessionId(null);
      setMessages([]);
      setView("home");
    }
    await refreshChats();
  }

  async function showMoreUnis() {
    const p = lastPayload?.profile;
    if (!p) return;
    const offset = (lastPayload?.cards?.length || 0) + extraCards.length;
    const country = p.destination_pref
      ? `&country=${encodeURIComponent(p.destination_pref)}`
      : "";
    const data = await api<{ cards: UniversityCard[]; has_more: boolean }>(
      `/api/universities?school=${encodeURIComponent(p.school_code)}&programme_type=${encodeURIComponent(p.programme_type)}&offset=${offset}${country}`,
    );
    setExtraCards((c) => [...c, ...data.cards]);
  }

  const cards = [...(lastPayload?.cards || []), ...extraCards];
  const profile = lastPayload?.profile;

  return (
    <div className="flex h-screen overflow-hidden bg-[#f7f6f4]">
      <Sidebar
        chats={chats}
        activeId={sessionId}
        search={search}
        onSearch={setSearch}
        onHome={() => {
          setView("home");
        }}
        onNew={onNew}
        onSelect={onSelect}
        onDelete={onDelete}
      />

      <main className="relative flex min-w-0 flex-1 flex-col">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-[#cbb8ff] opacity-40 blur-3xl" />
          <div className="absolute -right-10 top-10 h-72 w-72 rounded-full bg-[#dcd3ff] opacity-50 blur-3xl" />
          <div className="absolute bottom-0 right-20 h-64 w-64 rounded-full bg-[#eee4ff] opacity-60 blur-3xl" />
        </div>

        <header className="relative z-10 flex items-center px-8 py-5">
          <div className="text-[22px] font-semibold tracking-tight">NTU Exchange Planner</div>
        </header>

        <div ref={scroller} className="relative z-10 flex-1 overflow-y-auto">
          {view === "home" && messages.length === 0 ? (
            <HomeHero onCard={(p) => send(p)} />
          ) : (
            <div className="mx-auto w-full max-w-[820px] space-y-5 px-6 pb-32 pt-4">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
                  {m.role === "user" ? (
                    <div className="max-w-[80%] rounded-2xl bg-[#1b1b1b] px-4 py-3 text-[14px] text-white">
                      {m.content}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="whitespace-pre-wrap text-[15px] leading-7 text-[#222]">
                        {m.content}
                      </div>
                      {m.payload?.conversions?.map((c, j) => (
                        <div key={j} className="rounded-2xl bg-white px-4 py-3 text-[13px] text-[#333]">
                          {c.summary}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {cards.length > 0 && profile && (
                <div className="space-y-4">
                  {cards.map((c) => (
                    <UniCard
                      key={c.university_id}
                      card={c}
                      school={profile.school_code}
                      programmeType={profile.programme_type}
                      term={profile.preferred_semester}
                    />
                  ))}
                  {(lastPayload?.has_more || extraCards.length > 0) &&
                    (lastPayload?.total_universities || 0) > cards.length && (
                      <button
                        onClick={showMoreUnis}
                        className="rounded-full bg-white px-4 py-2 text-[13px] font-medium text-[#222] shadow-sm"
                      >
                        Show more universities
                      </button>
                    )}
                </div>
              )}

              {loading && <div className="text-[13px] text-[#888]">Planning…</div>}
            </div>
          )}
        </div>

        <div className="relative z-10 px-6 pb-6">
          <Composer value={input} onChange={setInput} onSend={() => send(input)} disabled={loading} />
        </div>
      </main>
    </div>
  );
}
