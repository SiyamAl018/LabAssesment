// Farm entity – Req 3
export interface Farm {
  id: string;
  name: string;              // canonical name
  owner_name?: string | null;
  village?: string | null;   // village or notes
  created_at?: string;
  aliases: FarmAlias[];
}

// Req 3: aliases with normalized form + confirmed flag
export interface FarmAlias {
  id: string;
  farm_id: string;
  alias: string;
  normalized_alias: string;
  confirmed: boolean;
}

export interface FarmInfo {
  owner_name: string;
  farm_name: string;
  location: string;
  plot: string;
  crop: string;
}

// Req 1 & 6: parsed fields – all nullable
export interface ParsedFields {
  farmer: string | null;
  plot: string | null;
  crop: string | null;
  problem: string | null;
  advice: string | null;
  follow_up: string | null;
  due_date: string | null;
  no_problem: boolean | null;
}

// Req 1 & 6: match_status
export type MatchStatus = 'matched' | 'needs_confirmation' | 'unmatched';

// API-level match envelope (keeps frontend backward-compatible)
export interface MatchResult {
  status: 'confident_match' | 'uncertain' | 'no_match';
  farm_id: string | null;
  candidates: { id: string; name: string; score: number }[];
}

// Req 2: visits table (raw_text never altered, optional audio_path)
export interface Visit {
  id: string;
  sequence: number;
  raw_text: string;          // verbatim, never altered – Req 2
  audio_path?: string | null; // optional audio – Req 2
  visit_date: string;
  created_at: string;
  parse_status: 'pending' | 'parsed' | 'failed';
  farm_id: string | null;
  farm_confirmed: boolean;
  match_status: MatchStatus; // DB form – Req 1 & 6
  parsed: ParsedFields;
  match: MatchResult;        // API form for backward compat
  farm_info: Partial<FarmInfo>;
  completed_by: string | null;
}

// Req 4: follow-up reminders
export interface Reminder {
  note_id: string;
  farm_id: string | null;
  farm_name: string | null;
  follow_up: string;
  due_date: string | null;
  completed_by: string | null;
}

export interface Followups {
  overdue: Reminder[];
  upcoming: Reminder[];
  undated: Reminder[];
  completed: Reminder[];
}

// Req 5 & 6: monthly report
export interface Report {
  month: string;
  total_visits: number;
  unique_farms: number;
  unmatched_visits: number;
  no_problem_count: number;
  problems: { note_id: string; text: string }[];
  advice: { note_id: string; text: string }[];
  visits: Visit[];
}
