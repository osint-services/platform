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
          expression: `(async () => {
            const status = document.querySelector('.MuiChip-label')?.textContent;
            const issue = document.querySelector('[role=alert]')?.textContent;
            if (status !== 'Services online') return { status, issue };
            try {
              const response = await fetch('http://127.0.0.1:80/datasets');
              const datasets = response.ok && Array.isArray(await response.json());
              return { status, datasets };
            } catch (error) {
              return { status, issue: error.message };
            }
          })()`,
          awaitPromise: true,
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
      if (result.datasets) {
        console.log('Whoisit reported Services online and the renderer reached the dataset API.');
        process.exit(0);
      }
      issue = result.issue || 'The packaged renderer could not read the dataset API.';
    }
  } catch {
    // Electron may still be starting.
  }
  await delay(1000);
}
throw new Error(issue || 'Whoisit did not report Services online.');
