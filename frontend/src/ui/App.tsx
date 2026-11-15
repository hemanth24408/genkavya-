import { useEffect, useState, type FormEvent } from 'react'
import { ArrowDown, ArrowDownToLine, ArrowRight, BookOpen, Check, ChevronDown, CircleAlert, Copy, Feather, Menu, Sparkles, X } from 'lucide-react'
import { generatePoetry } from '../services/generation'
import type { Candidate, CheckStatus } from '../types'

type ReaderTab = 'sanskrit' | 'meaning' | 'transliteration'
const statusText: Record<CheckStatus, string> = { passed: 'Passed', failed: 'Failed', unverified: 'Unverified' }
const sampleScenes = [
  ['Hanuman’s leap', 'Hanuman stands at the ocean’s edge, gathering his courage before leaping toward Lanka.'],
  ['Rama’s forest journey', 'Rama, Sita and Lakshmana walk beneath the quiet forest canopy as evening falls.'],
  ['The bridge to Lanka', 'The vanaras work together to build a bridge across the sea toward Lanka.'],
]

function Pill({ status, children }: { status: CheckStatus; children: string }) {
  return <span className={`pill ${status}`}><i />{children}</span>
}

function transliterate(text: string) {
  const consonants: Record<string, string> = { 'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ', 'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ', 'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ', 'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n', 'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'ś', 'ष': 'ṣ', 'स': 's', 'ह': 'h', 'ळ': 'ḷ' }
  const vowels: Record<string, string> = { 'अ': 'a', 'आ': 'ā', 'इ': 'i', 'ई': 'ī', 'उ': 'u', 'ऊ': 'ū', 'ऋ': 'ṛ', 'ॠ': 'ṝ', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au' }
  const marks: Record<string, string> = { 'ा': 'ā', 'ि': 'i', 'ी': 'ī', 'ु': 'u', 'ू': 'ū', 'ृ': 'ṛ', 'ॄ': 'ṝ', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'ṃ', 'ः': 'ḥ', 'ँ': 'm̐' }
  let output = ''
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    if (consonants[char]) {
      output += consonants[char]
      if (text[i + 1] === '्') i += 1
      else if (marks[text[i + 1]]) { i += 1; output += marks[text[i]] }
      else output += 'a'
    } else output += vowels[char] ?? marks[char] ?? (char === '।' ? '|' : char === '॥' ? '||' : char)
  }
  return output
}

function Brand({ footer = false }: { footer?: boolean }) {
  return <a className={`brand${footer ? ' footer-brand' : ''}`} href="#home" aria-label="GenKavya home">
    <span className="brand-mark"><Feather size={19} strokeWidth={1.5} /></span>
    <span className="brand-type">gen<span>kavya</span><small>VERSE, REIMAGINED</small></span>
  </a>
}

function CandidateValidation({ candidate }: { candidate: Candidate }) {
  const words = candidate.mandatory_words
  const grammarStatus: CheckStatus = candidate.grammar_status === 'verified' ? 'passed' : candidate.grammar_status === 'issues_found' ? 'failed' : 'unverified'
  return <div className="validation-grid">
    <section><h4>Mandatory words</h4><Pill status={words.status}>{words.status === 'passed' ? 'All words present' : words.status === 'failed' ? 'Some words missing' : 'Unverified'}</Pill>
      {words.present.length > 0 && <p className="validation-note">Matched: {words.present.map(word => `${word.english} · ${word.matched_form_devanagari}`).join(', ')}</p>}
      {words.missing_positions.length > 0 && <p className="validation-note">Missing positions: {words.missing_positions.join(', ')}</p>}
      {words.unresolved_positions.length > 0 && <p className="validation-note">Unresolved positions: {words.unresolved_positions.join(', ')}</p>}
      {words.explanation && <p className="validation-note">{words.explanation}</p>}
    </section>
    <section><h4>Meter · Anuṣṭubh</h4><Pill status={candidate.meter.status}>{statusText[candidate.meter.status]}</Pill>
      <div className="syllables">{candidate.meter.syllable_counts.map((count, index) => <span key={index}>Pāda {index + 1}<b>{count ?? '—'}</b></span>)}</div>
      {candidate.meter.explanation && <p className="validation-note">{candidate.meter.explanation}</p>}
    </section>
    <section><h4>Grammar</h4><Pill status={grammarStatus}>{candidate.grammar_status.toUpperCase()}</Pill></section>
    <section><h4>Duplicate detection</h4><Pill status={candidate.duplicate_candidate ? 'failed' : 'passed'}>{candidate.duplicate_candidate ? 'Duplicate candidate' : 'Unique candidate'}</Pill></section>
  </div>
}

export default function App() {
  const [scene, setScene] = useState('')
  const [words, setWords] = useState(['', '', '', ''])
  const [results, setResults] = useState<Candidate[] | null>(null)
  const [activeCandidate, setActiveCandidate] = useState(0)
  const [mode, setMode] = useState<'demo' | 'live' | null>(null)
  const [readerTab, setReaderTab] = useState<ReaderTab>('sanskrit')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [validationOpen, setValidationOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (window.location.hash) {
      window.requestAnimationFrame(() => document.querySelector(window.location.hash)?.scrollIntoView())
    }
  }, [])

  const enteredWords = words.filter(word => word.trim())
  const active = results?.[activeCandidate]
  const scrollToStudio = () => {
    document.getElementById('create')?.scrollIntoView({ behavior: 'smooth' })
    setMobileOpen(false)
  }
  const fillScene = (value: string) => {
    setScene(value)
    document.getElementById('scene')?.focus()
  }
  const copyPoem = async () => {
    if (!active) return
    try {
      await navigator.clipboard.writeText(active.padas.join('\n'))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch { setError('Clipboard access is unavailable in this browser.') }
  }
  const downloadBrief = () => {
    const content = `GenKavya · Composition brief\n\nRamayana moment\n${scene}\n\nWords to weave in\n${words.join(', ')}\n\nCandidate ${activeCandidate + 1}\n${active?.padas.join('\n') ?? ''}\n\n${active?.english_summary ?? ''}`
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }))
    link.download = `genkavya-brief-${activeCandidate + 1}.txt`
    link.click()
    URL.revokeObjectURL(link.href)
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (!scene.trim()) { setError('Describe a scene from the Ramayana to begin.'); return }
    if (enteredWords.length !== 4) { setError('Enter exactly four mandatory words, one in each field.'); return }
    if (words.some(word => !/^[A-Za-z]+(?:['’-][A-Za-z]+)*$/.test(word.trim()))) { setError('Each mandatory word should be one English word.'); return }
    setLoading(true)
    setResults(null)
    try {
      const output = await generatePoetry(scene.trim(), words.map(word => word.trim()))
      setResults(output.candidates)
      setMode(output.mode)
      setActiveCandidate(0)
      setReaderTab('sanskrit')
      window.setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong. Please try again.')
    } finally { setLoading(false) }
  }

  return <div className="site-shell">
    <header className="navbar">
      <Brand />
      <button className="mobile-menu" aria-label="Toggle navigation" onClick={() => setMobileOpen(!mobileOpen)}>{mobileOpen ? <X /> : <Menu />}</button>
      <nav className={mobileOpen ? 'nav-links mobile-visible' : 'nav-links'}>
        <a href="#home" onClick={() => setMobileOpen(false)}>Home</a>
        <a href="#how" onClick={() => setMobileOpen(false)}>How it works</a>
        <a href="#about" onClick={() => setMobileOpen(false)}>Our story</a>
        <button className="nav-cta" onClick={scrollToStudio}>Open poetry studio <ArrowRight size={16} /></button>
      </nav>
    </header>

    <main>
      <section className="hero" id="home">
        <div className="hero-copy">
          <div className="eyebrow"><i /> ANCIENT VERSE · NEW PERSPECTIVES</div>
          <h1>Where ancient wisdom<br /><span className="mobile-space"> </span>meets <em>artificial intelligence.</em></h1>
          <p>A new way to explore Sanskrit poetry. Bring a story from the Ramayana and four words. Make the inspiration your own.</p>
          <div className="hero-actions"><button className="primary-button" onClick={scrollToStudio}><Feather size={16} />Create your padyam<ArrowRight size={17} /></button><a className="text-link" href="#how">Discover the process <ArrowDown size={14} /></a></div>
          <div className="hero-footnote"><span>✳</span>Rooted in the Ramayana. Made for the curious.</div>
        </div>
        <div className="hero-art" aria-label="A layered illustration of a Ramayana inspired poetry brief">
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><span className="art-kicker">THE ART OF DATTA PADI</span>
          <div className="art-story"><span className="art-step">01</span><span className="art-overline">YOUR STORY</span><p>Rama’s journey.<br />Your perspective.</p><small>— FROM THE RAMAYANA</small><Feather className="story-feather" size={55} strokeWidth={.65} /></div>
          <div className="art-poem"><div className="art-poem-head"><span>A STORY, REIMAGINED IN VERSE</span><Feather size={16} /></div><div className="art-star">✳</div><div className="art-sanskrit">रामो विग्रहवान् धर्मः<br />साधुः सत्यपराक्रमः।<br />राजा सर्वस्य लोकस्य<br />देवानामिव वासवः॥</div><p>“Rama is righteousness embodied,<br />noble, and true in his valour.”</p><div className="art-poem-foot"><span>A VERSE FROM THE RAMAYANA</span><span>AN ANCIENT ART. A NEW VOICE.</span></div></div>
          <div className="art-words"><span className="art-step">02</span><span className="art-overline">YOUR CHOSEN WORDS</span><div><b>धर्म</b><b>वन</b><b>मैत्री</b><b>सेतु</b></div><small>Four words. Infinite possibilities.</small></div>
          <div className="art-seal"><span>✳</span><small>AI ADHYAYI</small></div><i className="art-dot dot-one"/><i className="art-dot dot-two"/><div className="art-caption"><i /> YOUR STORY. YOUR WORDS. TIMELESS POETRY. <i /></div>
        </div>
        <div className="hero-bottom"><span>Inspired by Dattapadi <b>•</b> Rooted in the Ramayana <b>•</b> Made for your imagination</span><span className="hero-bottom-right"><span>श्लोक</span><i /><small>A living tradition</small></span></div>
      </section>

      <section className="create-section" id="create">
        <div className="section-heading"><div><div className="eyebrow"><i /> THE POETRY STUDIO</div><h2>A moment. Four words.<br /><em>A world of poetry.</em></h2></div><p>Bring a scene from the Ramayana.<br />Give it your words. Let tradition inspire the rest.</p></div>
        <div className="workspace">
          <div className="workspace-top"><div className="compose-label"><span><Sparkles size={19} /></span>Compose your padyam</div><span className="studio-tag"><i /> Sanskrit · Anuṣṭubh</span></div>
          <div className="workspace-body">
            <form className="compose-form" onSubmit={submit} noValidate>
              <div className="workspace-title"><span className="step-number">01</span><div><h3>Your inspiration</h3><p>Every great verse begins with a story.</p></div></div>
              <label className="field-heading" htmlFor="scene"><span>Set a scene from the Ramayana</span><em>Make it yours</em></label>
              <textarea id="scene" value={scene} onChange={event => setScene(event.target.value)} placeholder="Picture Hanuman at the ocean’s edge, discovering the courage to leap toward Lanka…" rows={5} maxLength={1200} />
              <div className="textarea-bottom"><span>A character, a feeling, a moment — a few details are enough.</span><span>{scene.length} / 1200</span></div>
              <div className="sample-prompts"><span>Need a starting point?</span><div>{sampleScenes.map(([label, text]) => <button type="button" key={label} onClick={() => fillScene(text)}>{label}<ArrowRight size={12} /></button>)}</div></div>
              <div className="word-heading"><div className="workspace-title"><span className="step-number">02</span><div><h3>Four words to weave in</h3><p>Choose four English words to inspire your Sanskrit verse.</p></div></div><span className={`word-counter ${enteredWords.length === 4 ? 'complete' : ''}`}>{enteredWords.length} / 4</span></div>
              <div className="word-inputs">{words.map((word, index) => <label className="word-field" key={index}><span>WORD 0{index + 1}</span><input value={word} onChange={event => setWords(current => current.map((currentWord, currentIndex) => currentIndex === index ? event.target.value : currentWord))} placeholder={['forest', 'dawn', 'courage', 'journey'][index]} aria-label={`Word ${index + 1}`} pattern="[A-Za-z]+(['’-][A-Za-z]+)*" maxLength={40} /></label>)}</div>
              {error && <div className="error-message" role="alert"><CircleAlert size={16} />{error}</div>}
              <div className="generate-row"><div className="privacy-note"><i />Your imagination. An ancient art.</div><div className="generate-action"><button className="generate-button" type="submit" disabled={loading}>{loading ? <><span className="spinner" />Weaving your verses…</> : <><Sparkles size={16} />Preview my padyam<ArrowRight size={16} /></>}</button><small>Interactive design preview · AI generation is not connected.</small></div></div>
            </form>
            <aside className="guidance-panel"><div className="eyebrow"><BookOpen size={16} strokeWidth={1.4} /> A LITTLE GUIDANCE</div><h3>The story is ancient.<br /><em>The perspective is<br />yours.</em></h3><p>You don’t need to be a poet. Just bring a moment that means something to you.</p><div className="guidance-ornament"><i />काव्यम्<i /></div><h4>A thoughtful brief makes a difference</h4><ol><li><span>1</span>Focus on one scene, rather than the whole epic.</li><li><span>2</span>Tell us what the characters feel, not just what they do.</li><li><span>3</span>Choose words that bring your scene to life.</li></ol><div className="creative-brief"><span>YOUR CREATIVE BRIEF</span><i /><i /><i /><i /><i /><small>A story and four words. That’s all it takes.</small></div></aside>
          </div>
        </div>
        <div className="section-signoff">शब्दात् काव्यम् <i /> From a word, a world of poetry.</div>
      </section>

      <section className="results-section" id="results" aria-live="polite">
        {loading && <div className="loading-state"><div className="loading-star">✳</div><h3>Listening for the verse…</h3><p>Your scene is finding its Sanskrit voice.</p><div className="loading-line"><i /></div></div>}
        {results && active && <div className="results-card">
          <div className="results-heading"><div><div className="eyebrow"><i /> YOUR NEXT CHAPTER</div><h2>Your composition brief is ready.</h2></div><span className="preview-badge">{mode === 'demo' ? 'Design preview' : 'Generated with GenKavya'}</span></div>
          <div className="results-body">
            <div className="brief-column"><span className="result-overline">YOUR RAMAYANA MOMENT</span><p className="brief-scene">{scene}</p><span className="result-overline words-overline">WORDS TO WEAVE IN</span><div className="brief-words">{words.map((word, index) => <span key={`${index}-${word}`}>{word}</span>)}</div><p className="brief-note">This is your brief, not a generated poem. The traditional verse alongside it is a sample of the reading experience.</p><button className="refine-link" onClick={scrollToStudio}>Refine my story <ArrowRight size={23} /></button>
              <div className="candidate-list-label">YOUR FIVE COMPOSITIONS</div><div className="candidate-list">{results.map((candidate, index) => <button key={candidate.candidate_id} className={index === activeCandidate ? 'candidate-option selected' : 'candidate-option'} onClick={() => { setActiveCandidate(index); setValidationOpen(false) }}><span>{String(index + 1).padStart(2, '0')}</span><span>Candidate {index + 1}<small>{candidate.english_summary}</small></span><ArrowRight size={14} /></button>)}</div>
            </div>
            <div className="reader-card">
              <div className="reader-top"><span>A VERSE FROM THE RAMAYANA</span><Sparkles size={21} /></div>
              <div className="reader-tabs" role="tablist" aria-label="Verse presentation">{(['sanskrit', 'meaning', 'transliteration'] as ReaderTab[]).map(tab => <button role="tab" aria-selected={readerTab === tab} className={readerTab === tab ? 'active' : ''} key={tab} onClick={() => setReaderTab(tab)}>{tab === 'sanskrit' ? 'Sanskrit' : tab === 'meaning' ? 'Meaning' : 'Transliteration'}</button>)}</div>
              <div className={`reader-poem ${readerTab !== 'sanskrit' ? 'reader-translation' : ''}`} lang={readerTab === 'sanskrit' ? 'sa' : 'en'}>{readerTab === 'sanskrit' ? active.padas.map((pada, index) => <p key={`${active.candidate_id}-${index}`}>{pada}</p>) : readerTab === 'meaning' ? <p>{active.english_summary}</p> : active.padas.map((pada, index) => <p key={`${active.candidate_id}-${index}`}>{transliterate(pada)}</p>)}</div>
              <div className="reader-summary">{readerTab === 'meaning' ? 'ENGLISH SUMMARY' : readerTab === 'transliteration' ? 'IAST TRANSLITERATION' : 'CANDIDATE ' + String(activeCandidate + 1).padStart(2, '0')}</div>
              <div className="reader-actions"><button onClick={copyPoem}>{copied ? <Check size={18} /> : <Copy size={18} />}{copied ? 'Copied' : 'Copy sample verse'}</button><button onClick={downloadBrief}><ArrowDownToLine size={19} />Download brief</button></div>
              <button className="validation-toggle" onClick={() => setValidationOpen(!validationOpen)} aria-expanded={validationOpen}><span>Validation details</span><span>Independent checks <ChevronDown size={16} className={validationOpen ? 'turn' : ''} /></span></button>
              {validationOpen && <CandidateValidation candidate={active} />}
            </div>
          </div>
        </div>}
      </section>

      <section className="how-section" id="how"><div className="how-intro"><div className="eyebrow"><i /> A SIMPLE RITUAL</div><h2>From a thought<br />to a <em>śloka.</em></h2><p>Poetry carries meaning across centuries.<br />Find your own way into the tradition,<br />one scene at a time.</p><button onClick={scrollToStudio}>Find your first verse <ArrowRight size={18} /></button></div>
        <div className="how-steps"><div className="how-step"><span>01</span><div><h3>Picture the moment</h3><p>A quiet forest. An ocean to cross. A promise to keep. Describe a Ramayana scene in your own words.</p></div><i><Feather size={19} /></i></div><div className="how-step"><span>02</span><div><h3>Choose your four words</h3><p>Give your inspiration a direction. Four English words become the creative starting point for your Sanskrit composition.</p></div><i className="dev-icon">अ</i></div><div className="how-step"><span>03</span><div><h3>Explore a new expression</h3><p>Preview your creative brief and discover the Sanskrit reading experience, with meaning and transliteration alongside.</p></div><i>✳</i></div></div>
      </section>

      <section className="about-section" id="about"><div className="about-copy"><div className="eyebrow"><i /> A NOTE ON GENKAVYA</div><h2>Old stories.<br /><em>New ways of listening.</em></h2><p>Inspired by Dattapadi — the art of composing poetry around given words — Genkavya imagines a meeting of Sanskrit tradition and artificial intelligence. Every story is an invitation to read, reflect, and create.</p><em className="about-motto">Poetry, with a timeless soul.</em></div><div className="about-callout"><span>✳</span><h3>कल्पना च काव्यं च</h3><p>Imagination meets poetry.</p><button onClick={scrollToStudio}>Begin your story <ArrowRight size={17} /></button></div></section>
    </main>

    <footer className="footer"><Brand footer /><span className="footer-tagline">Ancient roots. Infinite possibilities.</span><div><a href="#about">Our story</a><a href="#how">How it works</a><span>© 2026 Genkavya</span></div></footer>
  </div>
}
