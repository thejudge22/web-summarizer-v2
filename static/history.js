(() => {
  const state = { summaries: [], selected: new Set(), selecting: false };
  const list = document.getElementById("history-list");
  const historyContent = document.getElementById("history-content");
  const request = async (path, options = {}) => {
    const response = await fetch(path, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "History action failed");
    }
    return response;
  };
  const relativeTime = (iso) => new Intl.RelativeTimeFormat(undefined, { numeric: "auto" })
    .format(Math.round((new Date(iso) - Date.now()) / 86400000), "day");
  const hostFor = (url) => {
    try { return new URL(url).hostname; } catch (_) { return url; }
  };
  const download = async (response, filename) => {
    const objectUrl = URL.createObjectURL(await response.blob());
    const link = Object.assign(document.createElement("a"), { href: objectUrl, download: filename });
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  };
  const setText = (element, value) => { element.textContent = String(value || ""); return element; };
  const render = () => {
    document.getElementById("selected-count").textContent = `${state.selected.size} selected`;
    document.getElementById("bulk-actions").classList.toggle("hidden", !state.selecting || state.selected.size === 0);
    document.getElementById("selection-mode-button").textContent = state.selecting ? "Cancel selection" : "Select summaries";
    list.replaceChildren();
    if (!state.summaries.length) {
      list.append(setText(document.createElement("p"), "No saved summaries yet."));
      list.lastChild.className = "p-4 text-sm text-gray-500";
      return;
    }
    state.summaries.forEach((item) => {
      const row = document.createElement("div");
      row.className = "flex items-start gap-2 border-b p-3";
      const checkbox = document.createElement("input");
      checkbox.className = "history-select mt-1";
      checkbox.type = "checkbox";
      checkbox.dataset.id = String(item.id);
      checkbox.checked = state.selected.has(item.id);
      checkbox.hidden = !state.selecting;
      checkbox.setAttribute("aria-label", `Select ${item.title}`);
      const link = document.createElement("a");
      link.href = `/summaries/${encodeURIComponent(item.id)}`;
      link.className = "min-w-0 flex-1";
      const title = setText(document.createElement("div"), item.title);
      title.className = "truncate font-medium text-gray-800";
      const meta = setText(document.createElement("small"), `${item.source_host || hostFor(item.source_url)} · ${relativeTime(item.created_at)}`);
      meta.className = "block truncate text-gray-500";
      link.append(title, meta);
      const actions = setText(document.createElement("button"), "Actions");
      actions.type = "button";
      actions.className = "history-actions rounded px-2 py-1 text-sm text-blue-700";
      actions.dataset.id = String(item.id);
      actions.setAttribute("aria-label", `Actions for ${item.title}`);
      row.append(checkbox, link, actions);
      list.append(row);
    });
  };
  const refresh = async () => {
    state.summaries = (await (await request("/api/summaries")).json()).summaries;
    render();
  };
  const actionFor = async (id) => {
    const action = window.prompt("Type rename, download, or delete");
    if (!action) return;
    if (action === "rename") {
      const title = window.prompt("New title");
      if (!title) return;
      await request(`/api/summaries/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) });
      await refresh();
    } else if (action === "download") {
      await download(await request(`/api/summaries/${id}/download`), "summary.md");
    } else if (action === "delete" && window.confirm("Delete this saved summary? This cannot be undone.")) {
      await request(`/api/summaries/${id}`, { method: "DELETE" });
      state.selected.delete(id);
      await refresh();
    }
  };
  document.getElementById("selection-mode-button").onclick = () => {
    state.selecting = !state.selecting;
    if (!state.selecting) state.selected.clear();
    render();
  };
  document.getElementById("history-toggle").onclick = () => {
    historyContent.classList.toggle("hidden");
    document.getElementById("history-toggle").setAttribute("aria-expanded", String(!historyContent.classList.contains("hidden")));
  };
  document.getElementById("bulk-download").onclick = async () => {
    await download(await request("/api/summaries/download-zip", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids: [...state.selected] }) }), "web-summaries.zip");
  };
  document.getElementById("bulk-delete").onclick = async () => {
    await request("/api/summaries/bulk-delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids: [...state.selected] }) });
    state.selected.clear();
    await refresh();
  };
  list.onchange = (event) => {
    if (!event.target.matches(".history-select")) return;
    const id = Number(event.target.dataset.id);
    event.target.checked ? state.selected.add(id) : state.selected.delete(id);
    render();
  };
  list.onclick = async (event) => {
    if (!event.target.matches(".history-actions")) return;
    try { await actionFor(Number(event.target.dataset.id)); } catch (error) { window.alert(error.message); }
  };
  window.summaryHistory = {
    refresh,
    prepend(summary) {
      if (!summary || !summary.id) return;
      state.summaries = [summary, ...state.summaries.filter((item) => item.id !== summary.id)];
      render();
    },
    remove(id) {
      state.summaries = state.summaries.filter((item) => item.id !== id);
      state.selected.delete(id);
      render();
    },
    openActions: actionFor,
  };
  refresh().catch((error) => {
    list.replaceChildren(setText(document.createElement("p"), error.message));
    list.firstChild.className = "p-4 text-sm text-red-700";
  });
})();
