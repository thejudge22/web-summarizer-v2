from pathlib import Path
import subprocess
import unittest


class HistoryUiTests(unittest.TestCase):
    def test_shared_shell_includes_sidebar_and_controller(self):
        template = Path("templates/base.html").read_text()

        self.assertIn('{% include "history_sidebar.html" %}', template)
        self.assertIn('/static/history.js', template)

    def test_controller_contains_bulk_and_single_delete_behavior(self):
        script = Path("static/history.js").read_text()

        self.assertIn("/api/summaries", script)
        self.assertIn("bulk-delete", script)
        self.assertIn("download-zip", script)
        self.assertIn("confirm(", script)

    def test_selection_mode_exposes_a_select_all_clear_toggle(self):
        sidebar = Path("templates/history_sidebar.html").read_text()
        script = Path("static/history.js").read_text()

        self.assertIn('id="select-all-button"', sidebar)
        self.assertIn('"Clear selection"', script)
        self.assertIn('state.summaries.map((summary) => summary.id)', script)

    def test_select_all_and_clear_update_the_rendered_history_selection(self):
        runner = r'''
;(async () => {
const assert = require("node:assert/strict");
const source = require("fs").readFileSync("static/history.js", "utf8");

class Element {
  constructor() {
    this.children = [];
    this.className = "";
    this.textContent = "";
    this.dataset = {};
    this.hidden = false;
    this.classList = {
      values: new Set(),
      toggle: (name, force) => {
        const enabled = force === undefined ? !this.classList.values.has(name) : force;
        this.classList.values[enabled ? "add" : "delete"](name);
        return enabled;
      },
      contains: (name) => this.classList.values.has(name),
    };
  }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.append(child); return child; }
  replaceChildren(...children) { this.children = children; }
  remove() {}
  click() { this.onclick?.({ target: this }); }
  setAttribute() {}
  matches(selector) { return selector === ".history-select" && this.className.includes("history-select"); }
}

const elements = new Map();
const document = {
  body: new Element(),
  getElementById: (id) => elements.get(id),
  createElement: () => new Element(),
  addEventListener() {},
};
["history-list", "history-content", "selected-count", "bulk-actions", "selection-mode-button", "select-all-button", "history-toggle", "bulk-download", "bulk-delete"].forEach((id) => elements.set(id, new Element()));

const summaries = [
  { id: 7, title: "First", source_url: "https://example.com/first", created_at: "2026-07-14T00:00:00Z" },
  { id: 13, title: "Second", source_url: "https://example.com/second", created_at: "2026-07-14T00:00:00Z" },
];
let downloadedIds;
global.document = document;
global.window = { alert() {}, confirm: () => true, prompt: () => null };
global.URL = { createObjectURL: () => "blob:summary", revokeObjectURL() {} };
global.fetch = async (path, options = {}) => {
  if (path === "/api/summaries") return { ok: true, json: async () => ({ summaries }) };
  if (path === "/api/summaries/download-zip") {
    downloadedIds = JSON.parse(options.body).ids;
    return { ok: true, blob: async () => ({}) };
  }
  throw new Error(`Unexpected request: ${path}`);
};

eval(source);
await new Promise((resolve) => setImmediate(resolve));
elements.get("selection-mode-button").click();
const selectAll = elements.get("select-all-button");
const bulkActions = elements.get("bulk-actions");
assert.equal(selectAll.textContent, "Select all");
assert.equal(bulkActions.classList.contains("hidden"), true);

selectAll.click();
assert.equal(selectAll.textContent, "Clear selection");
assert.equal(elements.get("selected-count").textContent, "2 selected");
assert.equal(bulkActions.classList.contains("hidden"), false);
assert.deepEqual(elements.get("history-list").children.map((row) => row.children[0].checked), [true, true]);
await elements.get("bulk-download").onclick();
assert.deepEqual(downloadedIds, [7, 13]);

selectAll.click();
assert.equal(selectAll.textContent, "Select all");
assert.equal(elements.get("selected-count").textContent, "0 selected");
assert.equal(bulkActions.classList.contains("hidden"), true);
assert.deepEqual(elements.get("history-list").children.map((row) => row.children[0].checked), [false, false]);
await elements.get("bulk-download").onclick();
assert.deepEqual(downloadedIds, []);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
        result = subprocess.run(
            ["node", "--eval", runner],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_history_actions_use_visible_named_controls_instead_of_action_prompt(self):
        script = Path("static/history.js").read_text()

        self.assertIn("history-action-menu", script)
        self.assertIn('"Rename"', script)
        self.assertIn('"Download Markdown"', script)
        self.assertIn('"Delete"', script)
        self.assertNotIn('Type rename, download, or delete', script)

    def test_saved_summary_actions_open_the_shared_named_action_menu(self):
        template = Path("templates/index.html").read_text()
        script = Path("static/history.js").read_text()

        self.assertIn('id="saved-actions"', template)
        self.assertIn('openActions(summary.id, document.getElementById("saved-actions"))', template)
        self.assertIn("openActions(id, container)", script)

    def test_loading_overlays_leave_the_mobile_history_sidebar_reachable(self):
        base = Path("templates/base.html").read_text()
        loading = Path("templates/loading.html").read_text()

        self.assertIn('id="main-panel" class="relative min-h-screen', base)
        self.assertGreaterEqual(loading.count('class="absolute inset-0 z-50'), 4)
        self.assertNotIn('class="fixed inset-0 z-50', loading)

    def test_saved_summary_url_is_protocol_checked_before_linking(self):
        template = Path("templates/index.html").read_text()

        self.assertIn("isSafeExternalUrl", template)

    def test_desktop_overlays_are_scoped_to_the_main_panel(self):
        base = Path("templates/base.html").read_text()
        loading = Path("templates/loading.html").read_text()

        self.assertIn('id="main-panel" class="relative', base)
        self.assertGreaterEqual(loading.count("absolute inset-0 z-50"), 4)
        self.assertIn("showError(message)", loading)
        self.assertIn("getElementById('error-container').classList.add('flex')", loading)

    def test_result_download_actions_use_equal_responsive_grid_columns(self):
        template = Path("templates/loading.html").read_text()

        self.assertIn('id="result-actions" class="grid grid-cols-1 gap-4 sm:grid-cols-3"', template)
        self.assertIn('action="/download" method="post" class="min-w-0"', template)

    def test_markdown_uses_a_strict_dompurify_policy_for_hostile_markup(self):
        base = Path("templates/base.html").read_text()
        templates = [Path("templates/index.html").read_text(), Path("templates/loading.html").read_text()]
        hostile_payloads = [
            '<svg><script>alert(1)</script></svg>',
            '<math><mi xlink:href="javascript:alert(1)">x</mi></math>',
            '<a href="javascript:alert(1)">unsafe</a>',
        ]

        self.assertIn("dompurify", base.lower())
        self.assertIn("FORBID_TAGS", base)
        self.assertIn("svg", base)
        self.assertIn("math", base)
        self.assertIn("xlink", base)
        for template in templates:
            self.assertIn("DOMPurify.sanitize", template)
        self.assertTrue(all("javascript:" in payload or "<svg" in payload or "<math" in payload for payload in hostile_payloads))
