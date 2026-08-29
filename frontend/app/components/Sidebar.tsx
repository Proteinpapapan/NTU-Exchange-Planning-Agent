"use client";

import type { ChatSummary } from "@/lib/api";

function dayLabel(iso: string): "Today" | "Yesterday" | "Earlier" {
  const d = new Date(iso);
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const then = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = (start.getTime() - then.getTime()) / 86400000;
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  return "Earlier";
}

export default function Sidebar({
  chats,
  activeId,
  search,
  onSearch,
  onHome,
  onNew,
  onSelect,
  onDelete,
}: {
  chats: ChatSummary[];
  activeId: string | null;
  search: string;
  onSearch: (v: string) => void;
  onHome: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const filtered = chats.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase()),
  );
  const groups: Record<string, ChatSummary[]> = { Today: [], Yesterday: [], Earlier: [] };
  for (const c of filtered) {
    groups[dayLabel(c.updated_at)].push(c);
  }

  return (
    <aside className="flex h-full w-[272px] shrink-0 flex-col bg-[#141414] text-[#f3f3f3]">
      <div className="flex flex-col gap-3 px-4 pt-5">
        <button
          onClick={onNew}
          className="flex h-11 items-center justify-center rounded-full bg-white text-[14px] font-semibold text-[#111] transition hover:bg-[#f4f4f4]"
        >
          +  New Chat
        </button>
        <label className="flex h-10 items-center gap-2 rounded-full bg-[#2a2a2a] px-4 text-[#9a9a9a]">
          <SearchIcon />
          <input
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search"
            className="w-full bg-transparent text-[13px] text-[#eee] outline-none placeholder:text-[#8a8a8a]"
          />
        </label>
      </div>

      <nav className="mt-5 px-3">
        <NavItem active label="Home" onClick={onHome} icon={<HomeIcon />} />
      </nav>

      <div className="mt-6 flex-1 overflow-y-auto px-2 pb-6">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8d8d8d]">
          Chats
        </div>
        {(["Today", "Yesterday", "Earlier"] as const).map((g) =>
          groups[g].length ? (
            <div key={g} className="mb-3">
              <div className="px-3 py-1 text-[11px] text-[#8a8a8a]">{g}</div>
              {groups[g].map((c) => (
                <button
                  key={c.session_id}
                  onClick={() => onSelect(c.session_id)}
                  className={`group flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-[13px] ${
                    activeId === c.session_id ? "bg-[#2a2a2a]" : "hover:bg-[#222]"
                  }`}
                >
                  <span className="text-[#9a9a9a]">
                    <BubbleIcon />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[#e8e8e8]">{c.title}</span>
                  <span
                    className="hidden text-[#777] group-hover:inline"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(c.session_id);
                    }}
                  >
                    ×
                  </span>
                </button>
              ))}
            </div>
          ) : null,
        )}
      </div>
    </aside>
  );
}

function NavItem({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] ${
        active ? "bg-[#2a2a2a] text-white" : "text-[#cfcfcf] hover:bg-[#1f1f1f]"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20L17 17" />
    </svg>
  );
}
function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" />
    </svg>
  );
}
function BubbleIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H9l-5 4V6z" />
    </svg>
  );
}
