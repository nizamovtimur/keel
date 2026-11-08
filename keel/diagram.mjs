// Draws one Keel diagram with Archify: render the candidate, run Archify's static checks
// on the drawing, and turn it into a page fragment in the page's own colours.
// Called by keel/diagram.py:  node diagram.mjs <archify dir> <temp dir>, the job as JSON on stdin.
// Prints one JSON line: {status: "pass", html} or {status: "fail", message}.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [home, tmp] = process.argv.slice(2);
const say = (o) => process.stdout.write(`${JSON.stringify(o)}\n`);
const cli = path.join(home, 'bin', 'archify.mjs');
const run = (...args) => spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });

try {
  const job = JSON.parse(fs.readFileSync(0, 'utf8'));
  const candidate = path.join(tmp, 'candidate.json');
  const drawing = path.join(tmp, 'diagram.html');
  fs.writeFileSync(candidate, JSON.stringify(job.candidate));

  const rendered = run('render', 'architecture', candidate, drawing);
  if (rendered.status !== 0 || !fs.existsSync(drawing)) {
    say({ status: 'fail', message: (rendered.stderr || rendered.stdout || 'render failed').trim().slice(-600) });
    process.exit(0);
  }
  const checked = run('check', drawing, '--json');
  let report = null;
  try { report = JSON.parse(checked.stdout); } catch { /* reported below */ }
  if (checked.status !== 0 || !report?.ok) {
    const failed = (report?.checks || []).filter((c) => !c.ok).map((c) => `${c.name}: ${(c.details || []).join('; ')}`);
    say({ status: 'fail', message: failed.join(' | ') || (checked.stderr || 'check failed').trim().slice(-600) });
    process.exit(0);
  }

  const shared = (f) => pathToFileURL(path.join(home, 'renderers', 'shared', f)).href;
  const { fragmentFigure, extractDiagramSvg } = await import(shared('embed.mjs'));
  const { readGraph, textAtWidth } = await import(shared('embed-interact.mjs'));
  const html = fs.readFileSync(drawing, 'utf8');
  const fit = textAtWidth(readGraph(extractDiagramSvg(html)), job.width);
  if (fit.labelPx < 12) {
    say({ status: 'fail', message: `labels come out ${fit.labelPx} px in a ${job.width} px column` });
    process.exit(0);
  }
  const fragment = fragmentFigure(html, {
    source: 'diagram.html', profile: 'host', idPrefix: job.idPrefix, caption: job.caption,
    interactive: true, details: job.details, map: job.map,
  });
  say({ status: 'pass', html: fragment, fit });
} catch (e) {
  say({ status: 'fail', message: String(e?.message || e).slice(0, 600) });
}
