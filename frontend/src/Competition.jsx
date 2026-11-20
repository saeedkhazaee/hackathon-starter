import React, { useEffect, useRef, useState } from 'react';

async function request(path, method = 'GET') {
  const response = await fetch(`/api/competition${path}`, { method });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not complete this action.');
  return body;
}

function save(data, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Competition({ onRunning, interactiveBusy, configured }) {
  const [state, setState] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const lock = useRef(false);
  const running = ['baseline', 'optimized'].some((p) => state?.[p]?.status === 'running');
  useEffect(() => { onRunning(running); }, [running, onRunning]);
  useEffect(() => {
    let stopped = false;
    let timer;
    async function poll() {
      try {
        const value = await request('');
        if (!stopped) setState(value);
      } catch { /* Connection status is shown by the app; keep saved results visible. */ }
      if (!stopped) timer = setTimeout(poll, 3000);
    }
    poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, []);
  async function action(phase) {
    if (lock.current) return;
    lock.current = true; setPending(true); setError('');
    try {
      await request(`/${phase}`, 'POST');
      setState(await request(''));
    } catch (err) { setError(err.message); }
    finally { lock.current = false; setPending(false); }
  }
  const disabled = !state || running || pending || interactiveBusy || !configured;
  return <section className="competition" aria-label="Competition benchmark">
    <div className="competition-intro"><div><span className="eyebrow">YOUR COMPETITION WORKLOAD IS INCLUDED</span><h2>Same work. Less waste.</h2><p>40 documents · 37 valid results · 3 expected arithmetic failures. No uploads needed.</p></div><span className="competition-tag">3 trials per benchmark</span></div>
    <div className="competition-setup"><strong>First, integrate NetGreener.</strong> Confirm it measures the processing workers in each fresh benchmark process. These buttons do not install monitoring.</div>
    <div className="competition-steps">
      {['baseline', 'optimized'].map((phase, index) => {
        const run = state?.[phase];
        const report = run?.report;
        return <article className="competition-step" key={phase}>
          <span className="step-number">0{index + 1}</span>
          <h3>{index === 0 ? 'Measure the baseline' : 'Optimize, then measure again'}</h3>
          <p>{index === 0 ? 'Before changing the pipeline, capture its current resource use.' : 'Use NetGreener to investigate waste, change the code, and run correctness tests.'}</p>
          <button className={`button ${index === 0 ? 'primary' : 'outline'}`} disabled={disabled || (index === 1 && state?.baseline?.status !== 'completed')} onClick={() => action(phase)}>
            {run?.status === 'running' ? `Running · ${run.trials.length}/3 trials finished` : `Run ${phase === 'baseline' ? 'baseline' : 'optimized benchmark'}`}
          </button>
          {phase === 'baseline' && run && <small>A new baseline replaces the current comparison. Earlier report files stay on disk.</small>}
          {run && <div className="benchmark-status" role="status"><strong>{run.status === 'completed' ? 'Benchmark complete' : run.status.replaceAll('_', ' ')}</strong>
            {run.trials.map((trial) => <div key={trial.number}>Trial {trial.number}<span>{trial.wall_seconds.toFixed(2)}s wall · {trial.cpu_seconds.toFixed(2)}s CPU</span></div>)}
            {run.status === 'running' && <p>Processing the full workload. Keep this machine idle; you can leave this page open.</p>}
            {run.error && <p className="amber">{run.error}</p>}
            {report && <><p>Each trial: 37 successful documents and 3 expected failures.</p><button className="text-button" onClick={() => save(report, `${phase}.json`)}>Download {phase} report ↓</button></>}
          </div>}
        </article>;
      })}
      <article className="competition-step"><span className="step-number">03</span><h3>Compare your results</h3><p>Check that outputs match and measurement conditions stayed the same.</p><button className="button outline" disabled={disabled || state?.optimized?.status !== 'completed' || state?.baseline?.status !== 'completed'} onClick={() => action('compare')}>Compare results</button>
        {state?.comparison && <div className="benchmark-status" role="status"><strong className="green">Output equivalence passed</strong><div>Local CPU reduction<span>{state.comparison.independent_parent_cpu_reduction_pct.toFixed(1)}%</span></div><div>Wall time reduction<span>{state.comparison.independent_wall_reduction_pct.toFixed(1)}%</span></div><p>Negative values mean resource use increased.</p><button className="text-button" onClick={() => save(state.comparison, 'comparison.json')}>Download comparison ↓</button></div>}
      </article>
    </div>
    {error && <div className="alert" role="alert">{error}</div>}
    <div className="competition-foot"><p>Each run makes paid Azure requests and may take several minutes. Preserve the same machine, packages, monitoring, model settings, and cache conditions.</p><p><strong>For judging:</strong> attach real NetGreener before/after evidence with worker coverage, passing tests, and your three decision records. Local timing alone does not establish scoring eligibility.</p></div>
  </section>;
}
