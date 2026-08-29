export const API = "/backend";

export type Programme = { code: string; name: string };

export type MappingRow = {
  mapping_id: number;
  host_module_code: string;
  host_module_title: string;
  ntu_module_code: string;
  ntu_module_title: string;
  ntu_module_type: string;
  credits: number;
  year: string;
  sem: string;
  has_details: boolean;
};

export type UniversityCard = {
  university_id: number;
  name: string;
  country: string;
  approved_count: number;
  programme_type: string;
  mappings_preview: MappingRow[];
  preview_shown: number;
};

export type ModuleConversion = {
  host_module_code: string;
  host_module_title: string;
  ntu_module_code: string;
  mapped_au: number;
  host_credits: number | null;
  host_credits_au: number | null;
};

export type UniversityBriefing = {
  name: string;
  country?: string | null;
  gem_program?: string | null;
  term?: string | null;
  source?: string | null;
  housing?: string | null;
  course_load_raw?: string | null;
  min_ects?: number | null;
  max_ects?: number | null;
  min_au?: number | null;
  max_au?: number | null;
  au_note?: string;
  gpa?: string | null;
  brochure_url?: string | null;
  error?: string | null;
  module_conversions?: ModuleConversion[];
};

export type Conversion = {
  kind: string;
  summary: string;
  details: Record<string, unknown>;
};

export type Profile = {
  school_code: string;
  school_name: string;
  preferred_semester: string;
  programme_type: string;
  destination_pref?: string | null;
};

export type Payload = {
  clarification?: string | null;
  narration?: string;
  cards?: UniversityCard[];
  total_universities?: number;
  conversions?: Conversion[];
  research?: string | null;
  profile?: Profile | null;
  has_more?: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  payload?: Payload;
};

export type ChatSummary = {
  session_id: string;
  title: string;
  folder: string | null;
  created_at: string;
  updated_at: string;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}
