export interface Farm { id: string; name: string; owner_name?: string | null; location?: string | null; aliases: string[] }
export interface FarmInfo { owner_name: string; farm_name: string; location: string; plot: string; crop: string }
export interface ParsedFields {
  farmer: string | null; plot: string | null; crop: string | null;
  problem: string | null; advice: string | null; follow_up: string | null;
  due_date: string | null; no_problem: boolean | null;
}
export interface Visit {
  id: string; raw_text: string; visit_date: string; parsed: ParsedFields;
  farm_info: Partial<FarmInfo>;
  parse_status: 'pending' | 'parsed' | 'failed'; farm_id: string | null; farm_confirmed: boolean;
  completed_by: string | null;
  match: { status: 'confident_match' | 'uncertain' | 'no_match'; farm_id: string | null; candidates: { id: string; name: string; score: number }[] };
}
export interface Reminder { note_id: string; farm_id: string | null; farm_name: string | null; follow_up: string; due_date: string | null; completed_by: string | null }
export interface Followups { overdue: Reminder[]; upcoming: Reminder[]; undated: Reminder[]; completed: Reminder[] }
export interface Report { month: string; total_visits: number; unique_farms: number; unmatched_visits: number; no_problem_count: number; problems: { note_id: string; text: string }[]; advice: { note_id: string; text: string }[]; visits: Visit[] }
