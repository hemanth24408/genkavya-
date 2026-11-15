import type { Candidate, GenerationResult } from '../types'

// Illustrative verses remain explicitly unverified: preview mode does not run the Sanskrit validators.
const demoCandidates: Candidate[] = [
  {
    candidate_id: 'demo-1',
    padas: ['वनमध्ये सीता विरहं स्मरति', 'रामो धनुषा धर्ममुदञ्चति', 'पुष्पाणि वातेन शनैः पतन्ति', 'फलानि शोकं शमयन्ति नूनम्'],
    english_summary: 'In the forest, Sita remembers her beloved while Rama stands steadfast in his duty.',
    duplicate_candidate: false,
    mandatory_words: { status: 'unverified', present: [], missing_positions: [], unresolved_positions: [1, 2, 3, 4], explanation: 'Preview text is illustrative; word resolution has not been run.' },
    meter: { status: 'unverified', syllable_counts: [null, null, null, null], explanation: 'Meter has not been checked in preview mode.' },
    grammar_status: 'unverified',
  },
  {
    candidate_id: 'demo-2',
    padas: ['शान्ते वने मृगाः चरन्ति', 'सीतायाः स्मृतिरुदेति हृदि', 'रामस्य बाणो धर्मरक्षकः', 'प्रभाते आशा पुनरागता'],
    english_summary: 'The quiet forest holds memory and the promise of hope at dawn.',
    duplicate_candidate: false,
    mandatory_words: { status: 'unverified', present: [], missing_positions: [], unresolved_positions: [1, 2, 3, 4] },
    meter: { status: 'unverified', syllable_counts: [null, null, null, null] },
    grammar_status: 'unverified',
  },
  {
    candidate_id: 'demo-3',
    padas: ['नदीतीरे वायुः शनैर्वहति', 'लक्ष्मणः पन्थानमवेक्षते', 'रामनाम हृदि दीप्यते', 'वनमार्गे धैर्यं प्रवर्धते'],
    english_summary: 'At the riverbank, Lakshmana keeps watch as Rama’s name gives courage.',
    duplicate_candidate: false,
    mandatory_words: { status: 'unverified', present: [], missing_positions: [], unresolved_positions: [1, 2, 3, 4] },
    meter: { status: 'unverified', syllable_counts: [null, null, null, null] },
    grammar_status: 'unverified',
  },
  {
    candidate_id: 'demo-4',
    padas: ['मेघाः शनैः नभसि सञ्चरन्ति', 'वनपुष्पाणि सुगन्धं वहन्ति', 'वीरस्य हृदयं न विचलति', 'धर्मपथे चरणं स्थापयति'],
    english_summary: 'Clouds drift above fragrant flowers while the hero holds to the path of dharma.',
    duplicate_candidate: false,
    mandatory_words: { status: 'unverified', present: [], missing_positions: [], unresolved_positions: [1, 2, 3, 4] },
    meter: { status: 'unverified', syllable_counts: [null, null, null, null] },
    grammar_status: 'unverified',
  },
  {
    candidate_id: 'demo-5',
    padas: ['अस्ताचले भानुरवसानमीयात्', 'आश्रमदीपो निशि दीप्यते', 'प्रतीक्षते जनकात्मजा धीरम्', 'प्रत्यागमनं रामस्य मङ्गलम्'],
    english_summary: 'As sunset falls, Sita waits patiently beneath the steady light of the hermitage.',
    duplicate_candidate: false,
    mandatory_words: { status: 'failed', present: [], missing_positions: [1, 2, 3, 4], unresolved_positions: [] },
    meter: { status: 'unverified', syllable_counts: [null, null, null, null] },
    grammar_status: 'unverified',
  },
]

export async function generatePoetry(scene: string, words: string[]): Promise<GenerationResult> {
  const endpoint = import.meta.env.VITE_GENKAVYA_API_URL
  if (!endpoint) {
    await new Promise(resolve => window.setTimeout(resolve, 1500))
    return { candidates: demoCandidates, mode: 'demo' }
  }

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scene, words }),
  })
  if (!response.ok) throw new Error(`Generation failed (${response.status}). Please try again.`)

  const payload = await response.json() as { candidates?: Candidate[]; validation?: { candidates?: Candidate[] } }
  const candidates = payload.validation?.candidates ?? payload.candidates
  if (!Array.isArray(candidates) || candidates.length !== 5) {
    throw new Error('The generation service returned an unexpected response. Expected five candidates.')
  }
  return { candidates, mode: 'live' }
}
