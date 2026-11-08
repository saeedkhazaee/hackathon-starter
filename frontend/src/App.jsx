import React, { useEffect, useRef, useState } from 'react';

const terminal = (status) => ['completed', 'failed', 'cancelled'].includes(status);
const pretty = (value) => String(value ?? '—').replaceAll('_', ' ');

function Icon({ name = 'file', size = 20 }) {
  const paths = {
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h5" /></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4" /></>,
    play: <path d="m8 5 11 7-11 7z" />,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    check: <path d="m5 12 4 4L19 6" />,
    download: <path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4" />,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    stop: <rect x="6" y="6" width="12" height="12" rx="2" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((error) => error.msg).join('; ');
    } catch { /* Never display raw server responses. */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function remember(id) {
  try {
    if (id) localStorage.setItem('docflow.job', id);
    else localStorage.removeItem('docflow.job');
  } catch { /* Persistence is optional. */ }
}

function download(value, name, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([typeof value === 'string' ? value : JSON.stringify(value, null, 2)], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function uploadBatch(files) {
  if (!files.length || files.length > 50) throw new Error('Choose between 1 and 50 documents.');
  if (files.length === 1 && files[0].name.toLowerCase().endsWith('.json')) {
    if (files[0].size > 48_000_000) throw new Error('An inbox JSON file must be smaller than 48 MB.');
    let batch;
    try { batch = JSON.parse(await files[0].text()); } catch { throw new Error('The inbox file must contain valid JSON.'); }
    if (!Array.isArray(batch.documents)) throw new Error('An inbox JSON file needs a documents array.');
    return batch;
  }
  if (files.some((file) => !/\.(txt|pdf|png)$/i.test(file.name))) throw new Error('Choose TXT, PDF or PNG documents, or one inbox JSON file.');
  if (files.some((file) => file.size === 0 || file.size > 4_000_000)) throw new Error('Each document must contain 1–4,000,000 bytes.');
  if (files.some((file) => file.name.length > 160)) throw new Error('Document filenames must be 160 characters or fewer.');
  if (files.reduce((sum, file) => sum + file.size, 0) > 32_000_000) throw new Error('The combined documents must be smaller than 32 MB.');
  const documents = [];
  for (const file of files) {
    const content_base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(',')[1]);
      reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
      reader.readAsDataURL(file);
    });
    documents.push({ document_id: crypto.randomUUID(), filename: file.name, versions: [{ content_base64 }] });
  }
  return { documents };
}

function Result({ document }) {
  if (!document) return <div className="inspector-empty"><Icon size={34} /><h3>A closer look</h3><p>Select a document to explore its processing history and extracted fields.</p></div>;
  const result = document.result;
  const fields = result?.fields ?? {};
  const items = fields.items ?? [];
  return <>
    <div className="inspector-title"><div><span className="eyebrow">DOCUMENT DETAILS</span><h3>{document.document_id}</h3></div><span className={`badge ${document.status}`}>{pretty(document.status)}</span></div>
    <div className="detail-meta"><span>Current stage <strong>{pretty(document.stage)}</strong></span><span>Attempts <strong>{document.attempt}</strong></span></div>
    {document.error && <div className="document-error"><strong>{pretty(document.error.code)}</strong><p>{document.error.message}</p></div>}
    {result && <>
      <div className="classification"><Icon /><strong>{pretty(result.classification.category)}</strong><span>{result.format?.toUpperCase()} · {result.pages} {result.pages === 1 ? 'page' : 'pages'}</span></div>
      <h4>Extracted fields</h4>
      <dl className="fields">{Object.entries(fields).filter(([key]) => key !== 'items').map(([key, value]) => <div key={key}><dt>{pretty(key)}</dt><dd>{String(value)}<small>{result.citations?.[key]?.text_line ? `Source line ${result.citations[key].text_line}` : 'No source line reported'}</small></dd></div>)}</dl>
      {items.length > 0 && <details className="line-items"><summary>{items.length.toLocaleString()} line items</summary><p>Showing the first {Math.min(50, items.length)}. Download results for all items. Amounts are integer cents.</p><div className="table-scroll"><table><thead><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Amount</th></tr></thead><tbody>{items.slice(0, 50).map((item, i) => <tr key={i}><td>{item.description}</td><td>{item.quantity}</td><td>{item.unit_cents}</td><td>{item.amount_cents}</td></tr>)}</tbody></table></div></details>}
    </>}
    <h4>Processing history</h4>
    <div className="attempts">{document.attempts.map((attempt) => <details key={attempt.attempt_id} open={attempt.status === 'processing'}><summary><span>Attempt {attempt.number}</span><span className={`badge ${attempt.status}`}>{pretty(attempt.status)}</span></summary><ol>{attempt.checkpoints.map((point, i) => <li key={i}><span>{pretty(point.stage)}{point.stage === 'ai_response' ? ` · ${point.input_tokens} in / ${point.output_tokens} out` : ''}</span><time>{new Date(point.at).toLocaleTimeString()}</time></li>)}</ol>{attempt.error && <p className="attempt-error">{attempt.error.message}</p>}</details>)}</div>
  </>;
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [jobId, setJobId] = useState(() => { try { return localStorage.getItem('docflow.job'); } catch { return null; } });
  const [job, setJob] = useState(null);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState('');
  const [pollError, setPollError] = useState('');
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [dragging, setDragging] = useState(false);
  const [label, setLabel] = useState('Document inbox');
  const [filenames, setFilenames] = useState({});
  const [resultsReady, setResultsReady] = useState(false);
  const fileInput = useRef(null);
  const submitLock = useRef(false);
  const active = Boolean(jobId && (!job || !terminal(job.status)));
  const busy = submitting || active;

  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function check() {
      try { setHealth(await api('/health', { signal: controller.signal })); }
      catch { if (!controller.signal.aborted) setHealth({ status: 'offline' }); }
      if (!controller.signal.aborted) timer = setTimeout(check, 6000);
    }
    check();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const controller = new AbortController();
    let timer;
    async function poll() {
      try {
        const data = await api(`/jobs/${jobId}/status`, { signal: controller.signal });
        setJob(data);
        setSelected((current) => current ?? data.documents[0]?.document_id);
        setPollError('');
        if (terminal(data.status)) {
          const complete = await api(`/jobs/${jobId}/results`, { signal: controller.signal });
          setJob(complete);
          setResultsReady(true);
          return;
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err.status === 404) {
          setError('This job is no longer available. Start a new run; jobs expire after a server restart or newer jobs.');
          setJobId(null); setJob(null); remember(null);
          return;
        }
        setPollError('Connection interrupted. Retrying automatically…');
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 1000);
    }
    poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [jobId]);

  async function start(getBatch, title) {
    if (submitLock.current || busy) return;
    submitLock.current = true; setSubmitting(true); setError('');
    try {
      const batch = await getBatch();
      const response = await api('/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(batch) });
      setFilenames(Object.fromEntries(batch.documents.map((document) => [document.document_id, document.filename])));
      setJob(null); setSelected(null); setFilter('all'); setQuery(''); setResultsReady(false);
      setLabel(title); setJobId(response.job_id); remember(response.job_id);
    } catch (err) { setError(err.message === 'Failed to fetch' ? 'Cannot reach the backend. Check that it is running on port 8000.' : err.message); }
    finally { submitLock.current = false; setSubmitting(false); }
  }

  async function cancel() {
    setCancelling(true); setError('');
    try { await api(`/jobs/${jobId}/cancel`, { method: 'POST' }); }
    catch (err) { setError(err.message); }
    finally { setCancelling(false); }
  }

  async function example() {
    try {
      const batch = await api('/samples/demo');
      download(batch.documents[0].versions[0].text, 'example-invoice.txt', 'text/plain');
    } catch { setError('Could not download the example. Check the backend connection.'); }
  }

  const documents = job?.documents ?? [];
  const completed = documents.filter((d) => d.status === 'completed').length;
  const failed = documents.filter((d) => d.status === 'failed').length;
  const settled = documents.filter((d) => terminal(d.status)).length;
  const attempts = documents.reduce((sum, d) => sum + d.attempt, 0);
  const visible = documents.filter((d) => (filter === 'all' || d.status === filter) && `${d.document_id} ${filenames[d.document_id] ?? ''}`.toLowerCase().includes(query.toLowerCase()));
  const elapsed = job?.started_at ? Math.max(0, ((job.completed_at ? Date.parse(job.completed_at) : Date.now()) - Date.parse(job.started_at)) / 1000).toFixed(1) : '0.0';
  const chosen = documents.find((d) => d.document_id === selected);

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="DocFlow home"><span className="brand-mark"><Icon /></span><span>docflow<span className="brand-sub">RESCUE WORKSPACE</span></span></a>
      <span className="sidebar-label">WORKSPACE</span>
      <a className="nav-item selected" href="#workspace"><Icon />Document inbox<span className="nav-dot" /></a>
      <a className="nav-item" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer"><Icon name="arrow" />API explorer</a>
      <div className="sidebar-note"><span className="small-orbit">↗</span><h3>Less waste.<br />Better processing.</h3><p>Follow each document from ingestion to a verified result.</p><span className="sidebar-tag">DOCFLOW RESCUE</span></div>
      <div className="sidebar-footer"><span className={`connection-dot ${health?.status === 'ok' ? 'online' : ''}`} /><div>{health?.status === 'ok' ? 'Backend connected' : health ? 'Backend offline' : 'Connecting…'}<small>Local workspace</small></div></div>
    </aside>

    <main id="workspace">
      <header className="topbar"><span>Workspace <span className="breadcrumb">/</span> <strong>Document inbox</strong></span><span className="mode-pill"><span />{health?.azure_configured ? 'Azure AI ready' : 'Azure setup needed'}</span></header>
      <div className="page-content">
        <div className="page-heading"><div><span className="eyebrow">DOCUMENT OPERATIONS</span><h1>Make sense of every document<span>.</span></h1><p>Process your inbox. Follow the work. Inspect the outcome.</p></div><span className="workspace-number">01 / INBOX</span></div>
        {error && <div className="alert" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
        {health?.status === 'offline' && <div className="alert" role="status">The backend is unavailable. Start DocFlow on port 8000; this page will reconnect automatically.</div>}
        <section className="intake-grid" aria-label="Start a processing job">
          <div className={`upload-card ${dragging ? 'dragging' : ''} ${busy ? 'disabled' : ''}`} onDragOver={(event) => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (!busy) start(() => uploadBatch([...event.dataTransfer.files]), 'Uploaded documents'); }}>
            <div className="upload-symbol"><Icon name="upload" size={27} /></div>
            <div><h2>Bring your documents</h2><p>Drop files here, or choose them from your computer.</p><span className="file-types">TXT · PDF · PNG · Inbox JSON</span></div>
            <input ref={fileInput} className="visually-hidden" type="file" aria-label="Upload documents" accept=".txt,.pdf,.png,.json" multiple disabled={busy} onChange={(event) => { const files = [...event.target.files]; if (files.length) start(() => uploadBatch(files), 'Uploaded documents'); event.target.value = ''; }} />
            <button className="button primary" disabled={busy} onClick={() => fileInput.current.click()}><Icon name="upload" size={17} />Choose files</button>
            <div className="upload-foot"><span>Up to 50 files · 4 MB per document</span><button className="text-button" onClick={example}>Get an example <span>↗</span></button></div>
          </div>
          <div className="sample-card"><div className="sample-top"><span className="eyebrow">START WITH A SAMPLE</span><span className="sample-count">40<span>DOCS</span></span></div><h2>A ready-to-run inbox.</h2><p>Invoices, purchase orders, receipts, and contracts—with recovery cases and validation failures to inspect.</p><div className="sample-actions"><button className="button dark" disabled={busy} onClick={() => start(() => api('/samples/demo'), 'Quick demo · 40 documents')}><Icon name="play" size={16} />Run quick demo</button><button className="button outline" disabled={busy} onClick={() => start(() => api('/samples/full'), 'Full workload · 40 documents')}>Full workload <Icon name="arrow" size={16} /></button></div><small>Both samples include 8 AI-assisted documents and make paid Azure requests. Expect 37 successes and 3 validation failures. The full workload has larger documents.</small></div>
        </section>

        <div className="support-note"><Icon size={15} /><span>Use the supported document format. Digital PDFs need extractable text; PNG scans need Tesseract.{health?.ocr_available === false ? ' OCR is not available on this server.' : ''} {health?.azure_configured === false ? 'Ask the organizer for the server .env before processing prose documents.' : 'Prose sections are sent to the configured Azure deployment.'}</span></div>

        <section className="job-section" aria-label="Processing job">
          <div className="section-heading"><div><h2>{jobId ? label : 'Your processing activity'}</h2><p>{submitting ? 'Preparing and submitting your documents…' : jobId ? `Job ${jobId.slice(0, 12)} · ${active ? 'Processing' : pretty(job?.status ?? 'loading')}` : 'Start a run to see document progress and results here.'}</p></div><div className="job-actions">{active && <button className="button outline" disabled={cancelling} onClick={cancel}><Icon name="stop" size={15} />{cancelling ? 'Cancelling…' : 'Cancel job'}</button>}{resultsReady && <button className="button outline" onClick={() => download(job, `docflow-${jobId}.json`)}><Icon name="download" size={16} />Download results</button>}</div></div>
          <div className="metrics"><div><span>DOCUMENTS</span><strong>{documents.length || '—'}</strong><small>{documents.length ? `${settled} finished` : 'Waiting for a run'}</small></div><div><span>COMPLETED</span><strong className="green">{job ? completed : '—'}</strong><small>Successfully validated</small></div><div><span>FAILED</span><strong className={failed ? 'amber' : ''}>{job ? failed : '—'}</strong><small>Review the error details</small></div><div><span>ATTEMPTS</span><strong>{job ? attempts : '—'}</strong><small>{job ? `${elapsed}s elapsed` : 'Includes processing retries'}</small></div></div>
          {job && <div className="metrics" aria-label="Azure request usage"><div><span>AZURE REQUESTS</span><strong>{job.ai_usage?.requests ?? 0}</strong><small>Actual inference attempts</small></div><div><span>INPUT TOKENS</span><strong>{(job.ai_usage?.input_tokens ?? 0).toLocaleString()}</strong><small>Reported by Azure</small></div><div><span>OUTPUT TOKENS</span><strong>{(job.ai_usage?.output_tokens ?? 0).toLocaleString()}</strong><small>Includes reasoning tokens</small></div><div><span>USAGE COVERAGE</span><strong>{job.ai_usage?.responses_with_usage ?? 0}/{job.ai_usage?.requests ?? 0}</strong><small>{job.ai_usage?.errors ?? 0} request errors · no billing estimate</small></div></div>}
          {job && <div className="progress-track" role="progressbar" aria-label="Finished documents" aria-valuenow={settled} aria-valuemin={0} aria-valuemax={documents.length}><div style={{ width: `${documents.length ? settled / documents.length * 100 : 0}%` }} /></div>}
          {pollError && <div className="connection-message" role="status">{pollError}</div>}
          {!job && <div className="empty-state"><span className="empty-icon"><Icon size={30} /></span><h3>{submitting || jobId ? 'Your inbox is on its way' : 'A clear view of your workflow'}</h3><p>{submitting || jobId ? 'Fetching the latest processing state…' : 'Upload a document or try the sample inbox. Every attempt and result will appear here.'}</p>{!jobId && !submitting && <button className="text-button" onClick={() => start(() => api('/samples/demo'), 'Quick demo · 40 documents')}>Try the quick demo <Icon name="arrow" size={16} /></button>}</div>}
          {job && <div className="results-layout"><div className="inbox-panel"><div className="table-toolbar"><input type="search" aria-label="Search documents" placeholder="Find a document…" value={query} onChange={(event) => setQuery(event.target.value)} /><select aria-label="Filter document status" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All statuses</option>{['completed', 'failed', 'processing', 'retrying', 'pending', 'cancelled'].map((state) => <option key={state} value={state}>{pretty(state)}</option>)}</select></div><div className="document-list" aria-label="Documents">{visible.length === 0 && <p className="no-matches">No documents match this filter.</p>}{visible.map((document) => <button className={`document-row ${selected === document.document_id ? 'current' : ''}`} key={document.document_id} onClick={() => setSelected(document.document_id)} aria-pressed={selected === document.document_id}><span className="document-icon"><Icon size={19} /></span><span className="document-name"><strong>{filenames[document.document_id] ?? document.document_id}</strong><small>{pretty(document.stage)} · {document.attempt} {document.attempt === 1 ? 'attempt' : 'attempts'}</small></span><span className={`badge ${document.status}`}>{pretty(document.status)}</span></button>)}</div></div><aside className="inspector" aria-label="Selected document"><Result document={chosen} /></aside></div>}
        </section>
        <footer className="page-footer"><span>DocFlow Rescue <span className="footer-divider">/</span> Document workspace</span><span>One inbox. Every step accounted for.</span></footer>
      </div>
    </main>
  </div>;
}
