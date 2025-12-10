#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const file = path.resolve(__dirname, '..', 'index.html');
const content = fs.readFileSync(file, 'utf8');

const re = /(?:mat|flu|tab|ph):\s*"([^"]+)"/g;
const ids = [];
let m;
while ((m = re.exec(content)) !== null) ids.push(m[1]);

const sets = { fluent: new Set(), tabler: new Set(), ph: new Set() };
ids.forEach(v => {
  const parts = v.split(':');
  if (parts.length !== 2) return;
  const [set, slug] = parts;
  if (set === 'fluent') sets.fluent.add(slug);
  if (set === 'tabler') sets.tabler.add(slug);
  if (set === 'ph') sets.ph.add(slug);
});

const makeUrl = (set, slug) => `https://icon-sets.iconify.design/${set}/${encodeURIComponent(slug)}/`;

async function checkOne(url) {
  try {
    const res = await fetch(url, { method: 'GET' });
    return res.status === 200;
  } catch (e) {
    return false;
  }
}

async function run() {
  const report = { fluent: {}, tabler: {}, ph: {} };
  const concurrency = 8;
  const queue = [];

  function enqueueChecks(setName, items) {
    for (const slug of items) {
      queue.push({ setName, slug, url: makeUrl(setName === 'ph' ? 'ph' : setName, slug) });
    }
  }

  enqueueChecks('fluent', sets.fluent);
  enqueueChecks('tabler', sets.tabler);
  enqueueChecks('ph', sets.ph);

  let idx = 0;
  async function worker() {
    while (idx < queue.length) {
      const i = idx++;
      const { setName, slug, url } = queue[i];
      const ok = await checkOne(url);
      report[setName][slug] = ok;
    }
  }

  const workers = Array.from({ length: concurrency }, () => worker());
  await Promise.all(workers);

  // Print summary of missing icons
  const missing = { fluent: [], tabler: [], ph: [] };
  for (const s of ['fluent','tabler','ph']) {
    for (const [slug, ok] of Object.entries(report[s])) {
      if (!ok) missing[s].push(slug);
    }
  }

  console.log(JSON.stringify({ total: { fluent: Object.keys(report.fluent).length, tabler: Object.keys(report.tabler).length, ph: Object.keys(report.ph).length }, missing }, null, 2));
}

run().catch(err => { console.error(err); process.exit(1); });
