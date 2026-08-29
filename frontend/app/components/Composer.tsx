"use client";

export default function Composer({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
}) {
  return (
    <form
      className="mx-auto flex w-full max-w-[820px] items-center gap-3 rounded-full border border-[#ececec] bg-white px-5 py-2 shadow-[0_8px_40px_rgba(40,20,80,0.06)]"
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
    >
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="type your prompt here."
        className="h-11 flex-1 bg-transparent text-[15px] outline-none placeholder:text-[#9a9a9a]"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex h-11 w-11 items-center justify-center rounded-full bg-[#c8f06c] text-[#1a1a1a] transition hover:bg-[#b6e45a] disabled:opacity-50"
        aria-label="Send"
      >
        <Arrow />
      </button>
    </form>
  );
}

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}
