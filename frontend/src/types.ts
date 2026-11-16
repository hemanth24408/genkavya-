export type CheckStatus = 'passed' | 'failed' | 'unverified'
export type Candidate = {
  candidate_id: string
  padas: [string, string, string, string]
  english_summary: string
  duplicate_candidate: boolean
  mandatory_words: { status: CheckStatus; present: { input_position: number; english: string; matched_form_devanagari: string }[]; missing_positions: number[]; unresolved_positions: number[]; explanation?: string | null }
  meter: { status: CheckStatus; syllable_counts: (number | null)[]; laghu_guru_patterns: (string | null)[]; checks: { check: string; status: CheckStatus; explanation: string }[]; explanation?: string | null; method?: string }
  grammar_status: 'verified' | 'issues_found' | 'unverified'
}
export type GenerationResult = { candidates: Candidate[] }
