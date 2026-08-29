"use client";

import { useEffect, useState } from "react";
import {
  api,
  type MappingRow,
  type UniversityBriefing,
  type UniversityCard,
} from "@/lib/api";

function mappingRank(m: MappingRow): number {
  const t = (m.ntu_module_type || "").toUpperCase().replace(/\s+/g, "");
  const code = (m.ntu_module_code || "").toUpperCase();
  if (t === "CORE" || t === "GER-CORE") return 0;
  if ((t.includes("MAJOR") && t.includes("PE")) || t === "2NDSPEC-PE" || t === "2ND-SPEC-PE") return 1;
  if (t === "BDE" || t === "UE" || code === "BDE") return 9;
  return 5;
}

function sortMappings(list: MappingRow[]): MappingRow[] {
  return [...list].sort((a, b) => {
    const d = mappingRank(a) - mappingRank(b);
    if (d) return d;
    return `${a.ntu_module_code}\0${a.host_module_code}`.localeCompare(
      `${b.ntu_module_code}\0${b.host_module_code}`,
    );
  });
}

export default function UniCard({
  card,
  school,
  programmeType,
  term,
}: {
  card: UniversityCard;
  school: string;
  programmeType: string;
  term?: string | null;
}) {
  const [rows, setRows] = useState<MappingRow[]>(() => sortMappings(card.mappings_preview));
  const [openId, setOpenId] = useState<number | null>(null);
  const [details, setDetails] = useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState(false);
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [briefing, setBriefing] = useState<UniversityBriefing | null>(null);

  const remaining = Math.max(0, card.approved_count - rows.length);

  useEffect(() => {
    let live = true;
    const preview = Math.max(card.mappings_preview.length, 5);
    api<{ mappings: MappingRow[] }>(
      `/api/universities/${card.university_id}/mappings?school=${encodeURIComponent(school)}&programme_type=${encodeURIComponent(programmeType)}&offset=0&limit=${preview}`,
    )
      .then((data) => {
        if (!live || !data.mappings.length) return;
        setRows((prev) => (prev.length > preview ? prev : sortMappings(data.mappings)));
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [card.university_id, school, programmeType, card.mappings_preview.length]);

  async function showMore() {
    setLoading(true);
    try {
      const data = await api<{ mappings: MappingRow[] }>(
        `/api/universities/${card.university_id}/mappings?school=${encodeURIComponent(school)}&programme_type=${encodeURIComponent(programmeType)}&offset=${rows.length}&limit=12`,
      );
      setRows((prev) => sortMappings([...prev, ...data.mappings]));
    } finally {
      setLoading(false);
    }
  }

  async function toggleDetails(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    const data = await api<{ details: Record<string, string> }>(`/api/mappings/${id}/details`);
    setDetails(data.details);
  }

  async function knowMore() {
    const nextOpen = !briefingOpen;
    setBriefingOpen(nextOpen);
    if (!nextOpen || briefing || briefingLoading) return;
    setBriefingLoading(true);
    try {
      const data = await api<UniversityBriefing>("/api/research", {
        method: "POST",
        body: JSON.stringify({
          university_id: card.university_id,
          name: card.name,
          country: card.country,
          term: term || undefined,
          school,
          programme_type: programmeType,
        }),
      });
      setBriefing(data);
    } catch {
      setBriefing({
        name: card.name,
        error: "Could not reach GEM Explorer just now.",
        module_conversions: [],
      });
    } finally {
      setBriefingLoading(false);
    }
  }

  return (
    <article className="overflow-hidden rounded-[22px] border border-[#eee] bg-white">
      <div className="flex items-start justify-between gap-4 px-5 py-4">
        <div>
          <h3 className="text-[16px] font-semibold text-[#1b1b1b]">{card.name}</h3>
          <p className="mt-1 text-[12px] text-[#7a7a7a]">
            {card.country} · {card.approved_count} approved mappings · {card.programme_type}
          </p>
        </div>
        <button
          type="button"
          onClick={knowMore}
          className="shrink-0 rounded-full bg-[#111] px-3 py-1.5 text-[12px] font-medium text-white"
        >
          {briefingOpen ? "Hide briefing" : "Know more"}
        </button>
      </div>

      {briefingOpen && (
        <div className="mx-5 mb-4 space-y-3 rounded-2xl bg-[#fafafa] p-4 text-[13px] leading-6 text-[#333]">
          <div className="text-[12px] font-semibold uppercase tracking-wide text-[#7b5cff]">
            University briefing
          </div>
          {briefingLoading && <p className="text-[#666]">Loading housing and AU conversion from GEM Explorer…</p>}
          {!briefingLoading && briefing && (
            <>
              {briefing.gem_program && (
                <p className="text-[12px] text-[#666]">
                  GEM Explorer: {briefing.gem_program}
                  {briefing.term ? ` · ${briefing.term}` : ""}
                </p>
              )}
              <section>
                <h4 className="font-semibold text-[#222]">Housing costs</h4>
                <p className="mt-0.5 whitespace-pre-wrap">
                  {briefing.housing
                    ? briefing.housing
                    : briefing.gem_program
                      ? "GEM Explorer did not list housing figures for this programme."
                      : briefing.error || "Could not reach GEM Explorer just now."}
                </p>
              </section>
              <section>
                <h4 className="font-semibold text-[#222]">AU conversion</h4>
                {briefing.max_ects != null && briefing.max_au != null ? (
                  <p className="mt-0.5">
                    Course load:{" "}
                    {briefing.min_ects != null && briefing.min_au != null
                      ? `${briefing.min_ects}–${briefing.max_ects} ECTS ≈ ${briefing.min_au}–${briefing.max_au} NTU AU`
                      : `${briefing.max_ects} ECTS ≈ ${briefing.max_au} NTU AU`}
                    {briefing.au_note ? ` (${briefing.au_note})` : ""}.
                  </p>
                ) : briefing.course_load_raw ? (
                  <p className="mt-0.5 whitespace-pre-wrap">{briefing.course_load_raw}</p>
                ) : (
                  <p className="mt-0.5">
                    GEM Explorer did not list a course-load figure. Host credits for mapped modules
                    are converted below using 2 ECTS ≈ 1 NTU AU.
                  </p>
                )}
                {(briefing.module_conversions || []).length > 0 && (
                  <table className="mt-2 w-full text-left text-[12px]">
                    <thead>
                      <tr className="text-[#8a8a8a]">
                        <th className="pb-1 font-medium">Host module</th>
                        <th className="pb-1 font-medium">Host credits</th>
                        <th className="pb-1 font-medium">≈ NTU AU</th>
                        <th className="pb-1 font-medium">Mapped AU</th>
                      </tr>
                    </thead>
                    <tbody>
                      {briefing.module_conversions!.map((row) => (
                        <tr key={`${row.host_module_code}-${row.ntu_module_code}`} className="border-t border-[#eee]">
                          <td className="py-1 pr-2">
                            {row.host_module_code}
                            {row.ntu_module_code ? ` → ${row.ntu_module_code}` : ""}
                          </td>
                          <td className="py-1">{row.host_credits ?? "—"}</td>
                          <td className="py-1">{row.host_credits_au ?? "—"}</td>
                          <td className="py-1">{row.mapped_au || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>
              {briefing.gpa && (
                <p className="text-[12px] text-[#666]">Minimum CGPA on GEM Explorer: {briefing.gpa}</p>
              )}
              {briefing.error && !briefing.housing && briefing.max_ects == null && (
                <p className="text-[12px] text-[#8a4b4b]">{briefing.error}</p>
              )}
              {briefing.brochure_url && (
                <a
                  href={briefing.brochure_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-[12px] text-[#7b5cff] underline-offset-2 hover:underline"
                >
                  Open GEM Explorer page
                </a>
              )}
            </>
          )}
        </div>
      )}

      <div className="px-5 pb-4">
        <table className="w-full text-left text-[12px]">
          <thead>
            <tr className="text-[#8a8a8a]">
              <th className="pb-2 font-medium">Host module</th>
              <th className="pb-2 font-medium">NTU module</th>
              <th className="pb-2 font-medium">AU</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.mapping_id} className="border-t border-[#f3f3f3] align-top">
                <td className="py-2 pr-3">
                  <div className="font-medium text-[#222]">{m.host_module_code}</div>
                  <div className="text-[#6b6b6b]">{m.host_module_title}</div>
                </td>
                <td className="py-2 pr-3">
                  <div className="font-medium text-[#222]">{m.ntu_module_code}</div>
                  {m.ntu_module_type && m.ntu_module_type.toUpperCase() !== m.ntu_module_code.toUpperCase() ? (
                    <div className="text-[11px] text-[#8a8a8a]">{m.ntu_module_type}</div>
                  ) : null}
                  <div className="text-[#6b6b6b]">{m.ntu_module_title}</div>
                </td>
                <td className="py-2">{m.credits || "—"}</td>
                <td className="py-2">
                  <button
                    type="button"
                    className="text-[#7b5cff] underline-offset-2 hover:underline"
                    onClick={() => toggleDetails(m.mapping_id)}
                  >
                    {openId === m.mapping_id ? "Hide" : "Details"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {openId && details && (
          <dl className="mt-3 space-y-2 rounded-2xl bg-[#fafafa] p-4 text-[12px] text-[#444]">
            {Object.entries(details).map(([k, v]) =>
              v ? (
                <div key={k}>
                  <dt className="font-semibold text-[#222]">{k}</dt>
                  <dd className="mt-0.5 whitespace-pre-wrap">{v}</dd>
                </div>
              ) : null,
            )}
          </dl>
        )}
        {remaining > 0 && (
          <button
            type="button"
            onClick={showMore}
            disabled={loading}
            className="mt-3 rounded-full border border-[#e5e5e5] px-3 py-1.5 text-[12px] font-medium text-[#333]"
          >
            {loading ? "Loading…" : `Show ${remaining} more mappings`}
          </button>
        )}
      </div>
    </article>
  );
}
