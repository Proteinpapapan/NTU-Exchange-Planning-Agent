"use client";

export default function HomeHero({
  onCard,
}: {
  onCard: (prompt: string) => void;
}) {
  const cards = [
    {
      title: "Find mapped modules",
      body: "See approved host ↔ NTU pairs for your degree.",
      prompt: "Show me previously mapped modules for my degree.",
    },
    {
      title: "GEM Explorer",
      body: "Semester-long partners with mapping history.",
      prompt: "I want to plan GEM Explorer Semester 1 (Fall).",
    },
    {
      title: "SUSEP planning",
      body: "Singapore university exchange with mapped mods.",
      prompt: "I want to plan SUSEP Sem 1 (Fall).",
    },
    {
      title: "AU & currency",
      body: "Convert AUs to ECTS and budgets into SGD.",
      prompt: "Convert 15 AU to ECTS. My budget is 8000 USD.",
    },
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8 pb-28 pt-10">
      <h1 className="text-center text-[42px] font-semibold tracking-[-0.03em] text-[#1b1b1b]">
        How can we <span className="text-[#7b5cff]">assist</span> you today?
      </h1>
      <p className="mt-3 max-w-[520px] text-center text-[15px] leading-6 text-[#6b6b6b]">
        Plan GEM Explorer and SUSEP using NTU Coursefinder mappings. I only ask
        for your degree programme and which of the four exchange terms you want.
      </p>
      <div className="mt-10 grid w-full max-w-[920px] grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <button
            key={c.title}
            onClick={() => onCard(c.prompt)}
            className="rounded-[22px] border border-[#efefef] bg-white p-5 text-left shadow-[0_10px_30px_rgba(40,20,80,0.04)] transition hover:-translate-y-0.5"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="text-[16px] font-semibold text-[#1b1b1b]">{c.title}</div>
              <span className="text-[#888]">↗</span>
            </div>
            <p className="mt-3 text-[13px] leading-5 text-[#6b6b6b]">{c.body}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
