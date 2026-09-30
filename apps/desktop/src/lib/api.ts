import { Experiment, SystemStatus, SearchResult, ChatMessage } from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/system/status`);
  if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const res = await fetch(`${API_BASE}/experiments`);
  if (!res.ok) throw new Error(`Failed to fetch experiments: ${res.statusText}`);
  return res.json();
}

export async function fetchExperiment(expNum: number): Promise<Experiment> {
  const res = await fetch(`${API_BASE}/experiments/${expNum}`);
  if (!res.ok) throw new Error(`Failed to fetch experiment ${expNum}: ${res.statusText}`);
  return res.json();
}

export async function searchManual(query: string, expNumber?: number): Promise<SearchResult[]> {
  let url = `${API_BASE}/search?q=${encodeURIComponent(query)}`;
  if (expNumber) {
    url += `&exp_number=${expNumber}`;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function startLLM(config: { threads: number; gpu_layers: number; context_size: number }): Promise<any> {
  const res = await fetch(`${API_BASE}/llm/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) throw new Error(`Failed to start LLM: ${res.statusText}`);
  return res.json();
}

export async function stopLLM(): Promise<any> {
  const res = await fetch(`${API_BASE}/llm/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop LLM: ${res.statusText}`);
  return res.json();
}

export function streamChat(
  messages: { role: string; content: string }[],
  experimentId: number | null,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: any) => void,
  onDebugTrace?: (trace: any) => void
) {
  fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      experiment_id: experimentId,
      temperature: 0.2,
      max_tokens: 1024,
      stream: true
    })
  })
    .then(async (response) => {
      if (!response.body) throw new Error('No response body for streaming');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6).trim();
            if (dataStr === '[DONE]') {
              onDone();
              return;
            }
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.debug_trace && onDebugTrace) {
                onDebugTrace(parsed.debug_trace);
              }
              if (parsed.content) {
                onChunk(parsed.content);
              }
            } catch {
              // ignore partial json
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      onError(err);
    });
}
