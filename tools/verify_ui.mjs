/** Local Chromium/CDP verification. No npm or application dependency required. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { createServer } from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const binary = process.env.BROWSER_BIN;
assert(binary, 'Set BROWSER_BIN to a Chrome/Chromium executable.');
const output = process.env.VERIFY_OUTPUT || mkdtempSync(path.join(tmpdir(), 'asm-ui-results-'));
mkdirSync(output, { recursive: true });
const profile = mkdtempSync(path.join(tmpdir(), 'asm-ui-chrome-'));
const port = await new Promise(resolve => {
  const socket = createServer();
  socket.listen(0, '127.0.0.1', () => { const port = socket.address().port; socket.close(() => resolve(port)); });
});
const origin = `http://127.0.0.1:${port}`;
const server = spawn(process.env.PYTHON_BIN || path.join(root, '.venv/bin/python'),
  ['-m', 'streamlit', 'run', 'tests/browser_app.py', '--server.address=127.0.0.1', `--server.port=${port}`, '--server.headless=true', '--server.fileWatcherType=none'],
  { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
let serverLog = '';
server.stdout.on('data', chunk => { serverLog += chunk; });
server.stderr.on('data', chunk => { serverLog += chunk; });
const browser = spawn(binary, ['--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-pipe', `--user-data-dir=${profile}`],
  { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
let sequence = 0, buffer = '', session, browserLog = '';
const waiting = new Map();
const exceptions = [];
const results = [];
browser.stderr.on('data', chunk => { browserLog += chunk; });
browser.stdio[4].on('data', chunk => {
  buffer += chunk.toString();
  let end;
  while ((end = buffer.indexOf('\0')) >= 0) {
    const raw = buffer.slice(0, end); buffer = buffer.slice(end + 1);
    if (!raw) continue;
    const message = JSON.parse(raw);
    if (waiting.has(message.id)) {
      const { resolve, reject, timer } = waiting.get(message.id);
      waiting.delete(message.id); clearTimeout(timer);
      if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails);
  }
});
function call(method, params = {}, target = session) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error(`CDP timeout: ${method}\n${browserLog.slice(-1000)}`)); }, 15000);
    waiting.set(id, { resolve, reject, timer });
    browser.stdio[3].write(JSON.stringify({ id, method, params, ...(target ? { sessionId: target } : {}) }) + '\0');
  });
}
async function evaluate(expression) {
  const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
  assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(expression) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    const error = await evaluate('document.querySelector("[data-testid=stException]")?.innerText');
    assert(!error, error);
    await pause(100);
  }
  throw new Error(`Page wait failed: ${expression}\n${serverLog.slice(-2000)}`);
}
async function navigate(route, title) {
  await call('Page.navigate', { url: origin + route });
  await until(`document.querySelector('h1')?.textContent === ${JSON.stringify(title)} && !!document.querySelector('.st-key-asm-content')`);
  await until(`document.body.innerText.includes('지금 새로고침') && document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state') === 'notRunning' && document.querySelectorAll('[data-testid="stSkeleton"], [data-testid="stSkeletonElement"]').length === 0`);
  await pause(450);
}
async function screenshot(name) {
  const { data } = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  writeFileSync(path.join(output, `${name}.png`), Buffer.from(data, 'base64'));
}
async function layout(label) {
  const result = await evaluate(`(() => {
    const content = document.querySelector('.st-key-asm-content');
    const visible = element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden' && !element.closest('details:not([open]) > div');
    const overflows = [...content.querySelectorAll('*')].filter(visible).filter(element => {
      if (element.closest('[data-testid=stDataFrame], [data-testid=stPlotlyChart], [data-testid=stCode], [data-testid=stJson], [data-testid=stDataEditor]')) return false;
      const rect = element.getBoundingClientRect();
      return rect.left < -1 || rect.right > innerWidth + 1;
    }).map(element => ({ tag: element.tagName, testid: element.dataset.testid, text: element.textContent.slice(0, 70) })).slice(0, 12);
    return { width: innerWidth, scrollWidth: document.documentElement.scrollWidth, titles: document.querySelectorAll('h1').length, overflows,
      background: getComputedStyle(document.querySelector('[data-testid=stApp]')).backgroundColor };
  })()`);
  results.push({ label, ...result });
  assert.equal(result.titles, 1, `${label}: H1 count`);
  assert(result.scrollWidth <= result.width + 1, `${label}: page overflow ${JSON.stringify(result)}`);
  assert.deepEqual(result.overflows, [], `${label}: content overflow ${JSON.stringify(result.overflows)}`);
}

async function press(key, code = key, modifiers = 0) {
  const virtualKey = { Tab: 9, Enter: 13, Escape: 27, ArrowDown: 40, ' ': 32 }[key];
  await call('Input.dispatchKeyEvent', { type: 'keyDown', key, code, modifiers, windowsVirtualKeyCode: virtualKey,
    ...(key === 'Enter' ? { text: '\r' } : key === ' ' ? { text: ' ' } : {}) });
  await call('Input.dispatchKeyEvent', { type: 'keyUp', key, code, modifiers, windowsVirtualKeyCode: virtualKey });
  await pause(180);
}
async function interactions() {
  for (const theme of ['light', 'dark']) {
    await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] });
    await navigate('/', '개요');
    const closed = await evaluate(`(() => { const e=document.querySelector('.st-key-asm-content summary'); e.focus(); return e.getBoundingClientRect().height; })()`);
    await press(' ', 'Space');
    assert(await evaluate(`document.querySelector('.st-key-asm-content details').open`), 'Space opens expander');
    const opened = await evaluate(`document.querySelector('.st-key-asm-content summary').getBoundingClientRect().height`);
    assert.equal(opened, closed, 'Expander trigger height stays stable');
    await screenshot(theme + '-expander-open');
    await evaluate(`document.querySelector('.st-key-asm-content summary').focus()`);
    await press('Enter');
    await until(`!document.querySelector('.st-key-asm-content details').open`);
    await evaluate(`document.querySelector('[data-testid=stSidebar] [role=combobox]').focus()`);
    await press('ArrowDown');
    await until(`!!document.querySelector('[role=listbox]')`);
    await screenshot(theme + '-select-open');
    await press('Escape');
    await until(`!document.querySelector('[role=listbox]')`);
    await press('Tab');
    const forward = await evaluate(`document.activeElement.outerHTML`);
    await press('Tab', 'Tab', 8);
    assert.notEqual(await evaluate(`document.activeElement.outerHTML`), forward, 'Shift+Tab moves focus');
    await evaluate(`document.querySelector('a[href$="/history"]').focus()`);
    await press('Enter');
    await until(`document.querySelector('h1')?.textContent === '작업 이력'`);
    await pause(700);
    await layout(theme + '-keyboard-navigation');
    await evaluate(`document.querySelector('.st-key-asm-content input').focus()`);
    await call('Input.insertText', { text: 'not-present' });
    await press('Enter');
    await until(`document.body.innerText.includes('검색 결과가 없습니다')`);
    await screenshot(theme + '-no-search-results');
    await evaluate(`document.querySelector('[data-testid=stSidebarNav] a[href$="/"]').click()`);
    await until(`document.querySelector('h1')?.textContent === '개요'`);
    await evaluate(`history.back()`);
    await until(`document.querySelector('h1')?.textContent === '작업 이력'`);
    assert.equal(await evaluate(`document.querySelector('.st-key-asm-content input').value`), 'not-present', 'Browser back preserves search');
    await evaluate(`history.forward()`);
    await until(`document.querySelector('h1')?.textContent === '개요'`);
    results.push({ label: theme + '-interactions', passed: true });
    for (const [route, title] of [['/', '개요'], ['/history', '작업 이력'], ['/settings', '설정 · 출처 · 진단']]) {
      await navigate(route, title);
      await evaluate(`(() => { const s=document.createElement('style'); s.id='text-zoom-test'; s.textContent='html { font-size: 200% !important; }'; document.head.append(s); })()`);
      await pause(500);
      await layout(theme + '-200-percent-text-' + route);
      await screenshot(theme + '-200-text-' + (route.slice(1) || 'overview'));
    }
  }
  await navigate('/', '개요');
  // The theme chooser belongs to Streamlit, not a duplicate application widget.
  writeFileSync(path.join(output, 'theme-menu-dom.json'), JSON.stringify(await evaluate(`({menus:[...document.querySelectorAll('[id*=Menu], [data-testid*=Menu], [aria-haspopup]')].map(e=>e.outerHTML.slice(0,1500))})`), null, 2));
  assert.deepEqual(exceptions, [], 'Browser runtime exceptions');
}

async function themeControls() {
  await navigate('/', '개요');
  const controls = await evaluate(`({font: getComputedStyle(document.documentElement).fontSize,
    inputs: [...document.querySelectorAll('[data-testid=stSidebar] input')].map(e=>({role:e.getAttribute('role'), height:e.getBoundingClientRect().height, html:e.parentElement.outerHTML.slice(0,1600)})),
    captions: [...document.querySelectorAll('[data-testid=stCaptionContainer]')].slice(0,3).map(e=>({color:getComputedStyle(e).color, opacity:getComputedStyle(e).opacity}))})`);
  writeFileSync(path.join(output, 'controls.json'), JSON.stringify(controls, null, 2));
  for (const [name, color] of [['Dark', 'rgb(15, 20, 28)'], ['Light', 'rgb(247, 248, 250)']]) {
    await evaluate(`(() => { if (!document.querySelector('[data-testid=stThemeSwitcher]')) document.querySelector('[data-testid=stMainMenuButton]').click(); })()`);
    await until(`!!document.querySelector('[data-testid=stThemeSwitcher]')`);
    await screenshot(name.toLowerCase() + '-theme-menu');
    await evaluate(`([...document.querySelectorAll('[role=menuitemradio]')].find(e=>e.textContent.trim().endsWith(${JSON.stringify(name)}))).click()`);
    await until(`getComputedStyle(document.querySelector('[data-testid=stApp]')).backgroundColor === ${JSON.stringify(color)}`);
    results.push({label: 'native-theme-' + name, passed:true});
  }
}

try {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    assert(server.exitCode === null, `Streamlit exited: ${serverLog}`);
    try { if ((await fetch(origin + '/_stcore/health')).ok) break; } catch {}
    await pause(100);
  }
  await call('Browser.getVersion', {}, null);
  const { targetId } = await call('Target.createTarget', { url: 'about:blank' }, null);
  ({ sessionId: session } = await call('Target.attachToTarget', { targetId, flatten: true }, null));
  await call('Page.enable'); await call('Runtime.enable'); await call('Network.enable');
  await call('Network.setBlockedURLs', { urls: ['https://*'] });
  await call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await navigate('/', '개요');
  if (process.env.VERIFY_REQUEST_TOOLS) {
    for (const theme of ['light', 'dark']) {
      await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] });
      for (const width of [375, 1440]) {
        await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
        await navigate('/history', '작업 이력');
        await until(`!!document.querySelector('input[aria-label="추적할 요청"]')`);
        assert(await evaluate(`document.body.innerText.includes('호출 2건') && document.body.innerText.includes('pytest -q')`), 'First request calls and input');
        await layout(`${theme}-${width}-request-tools`);
        await evaluate(`document.querySelector('input[aria-label="추적할 요청"]').scrollIntoView({block:'center'})`);
        await screenshot(`${theme}-${width}-request-tools`);
        await evaluate(`document.querySelector('input[aria-label="도구 호출 상세"]').focus()`);
        await press('ArrowDown'); await press('ArrowDown'); await press('Enter');
        await until(`document.body.innerText.includes('파일 없음')`);
        await screenshot(`${theme}-${width}-failed-tool`);
        await evaluate(`document.querySelector('input[aria-label="추적할 요청"]').focus()`);
        await press('ArrowDown'); await press('ArrowDown'); await press('Enter');
        await until(`document.querySelector('input[aria-label="추적할 요청"]')?.value.includes('followup')`);
        await until(`document.body.innerText.includes('호출 1건') && document.querySelector('input[aria-label="도구 호출 상세"]')?.value.includes('결과 미확인')`);
        await screenshot(`${theme}-${width}-pending-tool`);
        results.push({label:`${theme}-${width}-tool-selection`, passed:true});
      }
    }
    assert.deepEqual(exceptions, [], 'Browser runtime exceptions');
  } else if (process.env.VERIFY_DATE_AXES) {
    for (const theme of ['light', 'dark']) {
      await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] });
      for (const width of [375, 1440]) {
        await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
        await navigate('/', '개요');
        const charts = await evaluate(`[...document.querySelectorAll('[data-testid=stPlotlyChart]')].filter(e=>!e.closest('details')).map(e=>[...e.querySelectorAll('.xtick text')].map(t=>t.textContent))`);
        assert.equal(charts.length, 2, 'Overview daily token and duration charts');
        for (const labels of charts) {
          assert(labels.length > 0, 'Date labels are visible');
          assert.equal(new Set(labels).size, labels.length, 'No repeated calendar date labels');
        }
        results.push({label: `${theme}-${width}-daily-date-labels`, charts});
        for (let index = 0; index < charts.length; index++) {
          await evaluate(`[...document.querySelectorAll('[data-testid=stPlotlyChart]')].filter(e=>!e.closest('details'))[${index}].scrollIntoView({block:'center'})`);
          await screenshot(`${theme}-${width}-daily-${index}`);
        }
      }
    }
    assert.deepEqual(exceptions, [], 'Browser runtime exceptions');
  } else if (process.env.VERIFY_THEME) {
    await themeControls();
  } else if (process.env.VERIFY_INTERACTIONS) {
    await interactions();
    await themeControls();
  } else if (process.env.VERIFY_PROBE) {
    writeFileSync(path.join(output, 'dom.json'), JSON.stringify(await evaluate(`({text: document.body.innerText, app:document.querySelector('[data-testid=stApp]').outerHTML.slice(0,500), captions:[...document.querySelectorAll('[data-testid=stCaptionContainer],.stCaption')].slice(0,4).map(e=>({html:e.outerHTML,color:getComputedStyle(e).color,opacity:getComputedStyle(e).opacity})), buttons: [...document.querySelectorAll('button')].map(e=>({text:e.innerText,aria:e.getAttribute('aria-label'),testid:e.dataset.testid})), links: [...document.querySelectorAll('a')].map(e=>({text:e.innerText,href:e.getAttribute('href')})), html:document.querySelector('.st-key-asm-content').outerHTML.slice(0,12000)})`), null, 2));
    await screenshot('overview');
  } else {
    const pages = [['/', '개요'], ['/history', '작업 이력'], ['/reviews', '회고·개선'], ['/agent-analysis', '프로젝트·에이전트 분석'], ['/analytics', '기간 분석'], ['/orchestration', '오케스트레이션'], ['/settings', '설정 · 출처 · 진단']];
    for (const theme of ['light', 'dark']) {
      await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] });
      for (const [width, height] of [[320, 850], [375, 850], [768, 1024], [1024, 900], [1440, 1000], [1920, 1080], [812, 375]]) {
        await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
        for (const [route, title] of pages) {
          await navigate(route, title);
          const name = `${theme}-${width}-${route.slice(1) || 'overview'}`;
          await screenshot(name);
          await layout(name);
        }
        console.log(`${theme}: ${width}×${height}, 7 pages passed`);
      }
    }
    assert.deepEqual(exceptions, [], 'Browser runtime exceptions');
  }
  console.log(`UI verification output: ${output}`);
} finally {
  writeFileSync(path.join(output, 'results.json'), JSON.stringify({ results, exceptions }, null, 2));
  writeFileSync(path.join(output, 'server.log'), serverLog);
  try { await call('Browser.close', {}, null); } catch {}
  browser.kill(); server.kill();
  for (const { timer } of waiting.values()) clearTimeout(timer);
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
