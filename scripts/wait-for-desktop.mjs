import { setTimeout as delay } from 'node:timers/promises';

async function readStatus(debuggerUrl) {
  const socket = new WebSocket(debuggerUrl);
  try {
    return await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Desktop status probe timed out')), 3000);
      socket.addEventListener('open', () => socket.send(JSON.stringify({
        id: 1,
        method: 'Runtime.evaluate',
        params: {
          expression: `({
            status: document.querySelector('.MuiChip-label')?.textContent,
            issue: document.querySelector('[role=alert]')?.textContent,
          })`,
          returnByValue: true,
        },
      })));
      socket.addEventListener('error', () => {
        clearTimeout(timeout);
        reject(new Error('Could not connect to the Electron debugger'));
      });
      socket.addEventListener('message', ({ data }) => {
        const response = JSON.parse(data);
        if (response.id !== 1) return;
        clearTimeout(timeout);
        resolve(response.result?.result?.value);
      });
    });
  } finally {
    socket.close();
  }
}

const deadline = Date.now() + 240_000;
let issue;
while (Date.now() < deadline) {
  try {
    const response = await fetch('http://127.0.0.1:9222/json/list', { signal: AbortSignal.timeout(2000) });
    const pages = await response.json();
    const desktop = pages.find((page) => page.type === 'page' && page.url.startsWith('file:'));
    const result = desktop && await readStatus(desktop.webSocketDebuggerUrl);
    if (result?.status === 'Service issue') {
      issue = result.issue;
      break;
    }
    if (result?.status === 'Services online') {
      console.log('Whoisit reported Services online.');
      process.exit(0);
    }
  } catch {
    // Electron may still be starting.
  }
  await delay(1000);
}
throw new Error(issue || 'Whoisit did not report Services online.');
