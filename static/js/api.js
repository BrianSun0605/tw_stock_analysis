async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `請求失敗（${response.status}）`);
  return payload;
}

export async function searchStocks(query, signal) {
  const response = await fetch(`/search?q=${encodeURIComponent(query)}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  return parseResponse(response);
}

export async function startAnalysis(query) {
  const response = await fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query }),
  });
  return parseResponse(response);
}

export function streamAnalysis(taskId, handlers) {
  const source = new EventSource(`/stream/${encodeURIComponent(taskId)}`);
  source.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "ping") return;
    if (message.type === "log") handlers.log?.(message.msg);
    if (message.type === "result") handlers.result?.(message.data);
    if (message.type === "done") {
      handlers.done?.(message.filename);
      source.close();
    }
    if (message.type === "error") {
      handlers.error?.(message.msg);
      source.close();
    }
  };
  source.onerror = () => {
    handlers.error?.("與分析服務的連線中斷，請重新嘗試。");
    source.close();
  };
  return source;
}

export async function shutdown(token) {
  const response = await fetch("/shutdown", {
    method: "POST",
    headers: { "X-Shutdown-Token": token, Accept: "application/json" },
  });
  return parseResponse(response);
}
