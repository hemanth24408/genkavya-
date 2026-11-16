import type { Candidate, GenerationResult } from '../types'

type ApiPayload = {
  validation?: { candidates?: Candidate[] }
  detail?: string | { msg?: string }[]
}

export type DemoGenerationResult = GenerationResult & {
  scene: string
  words: string[]
  label: string
  source: string
}

export async function generatePoetry(scene: string, words: string[]): Promise<GenerationResult> {
  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scene, words }),
  })

  const payload = await response.json().catch(() => null) as ApiPayload | null
  if (!response.ok) {
    const detail = payload?.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail) ? detail.map(item => item.msg || 'Invalid request').join('; ') : null
    throw new Error(message || `Generation failed (${response.status}). Please try again.`)
  }

  const candidates = payload?.validation?.candidates
  if (!Array.isArray(candidates) || candidates.length !== 5) {
    throw new Error('The generation service returned an unexpected response. Expected five candidates.')
  }
  return { candidates }
}

export async function loadGeneratedDemo(): Promise<DemoGenerationResult> {
  const demoPath = '/demo/genkavya-demo.json'
  let response: Response
  try {
    response = await fetch(demoPath)
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : String(cause)
    throw new Error(`Could not fetch ${demoPath}: ${detail}`)
  }

  let payload: {
    validation?: { candidates?: Candidate[] }
    demo?: { scene?: string; words?: string[]; label?: string; source?: string }
  }
  try {
    payload = await response.json() as typeof payload
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : String(cause)
    throw new Error(`Could not parse ${demoPath}: ${detail}`)
  }
  if (!response.ok) {
    throw new Error(`Could not load ${demoPath}: HTTP ${response.status} ${response.statusText}`)
  }

  const candidates = payload?.validation?.candidates
  const demo = payload?.demo
  if (!Array.isArray(candidates) || candidates.length !== 5 ||
      !demo?.scene || !Array.isArray(demo.words) || demo.words.length !== 4 || !demo.label || !demo.source) {
    throw new Error(`${demoPath} loaded, but its demo metadata or five validation results are incomplete.`)
  }
  return { candidates, scene: demo.scene, words: demo.words, label: demo.label, source: demo.source }
}
