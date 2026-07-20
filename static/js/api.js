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

export async function startAnalysis(query, language = "zh-TW") {
  const response = await fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query, language }),
  });
  return parseResponse(response);
}

export async function getTask(taskId) {
  const response = await fetch(`/task/${encodeURIComponent(taskId)}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return parseResponse(response);
}

export async function requestReport(taskId) {
  const response = await fetch(`/task/${encodeURIComponent(taskId)}/report`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  return parseResponse(response);
}

export async function cancelTask(taskId) {
  const response = await fetch(`/task/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  return parseResponse(response);
}

export function streamAnalysis(taskId, handlers, after = 0) {
  const cursor = Math.max(0, Number(after) || 0);
  const source = new EventSource(`/stream/${encodeURIComponent(taskId)}?after=${cursor}`);
  let terminal = false;

  source.onopen = () => handlers.connection?.("connected");
  source.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "ping") return;
      handlers.cursor?.(Number(message.id) || 0);
      if (message.type === "log") handlers.log?.(message.msg);
      if (message.type === "result") handlers.result?.(message.data);
      if (message.type === "report") handlers.report?.(message);
      if (message.type === "done") {
        terminal = true;
        handlers.done?.(message.filename);
        source.close();
      }
      if (message.type === "error") {
        terminal = true;
        handlers.error?.(message.msg);
        source.close();
      }
      if (message.type === "report_error") {
        terminal = true;
        handlers.reportError?.(message.msg);
        source.close();
      }
      if (message.type === "cancelled") {
        terminal = true;
        handlers.cancelled?.(message.msg);
        source.close();
      }
    } catch (error) {
      handlers.clientError?.(error);
    }
  };
  source.onerror = () => {
    if (!terminal) handlers.connection?.("reconnecting");
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
