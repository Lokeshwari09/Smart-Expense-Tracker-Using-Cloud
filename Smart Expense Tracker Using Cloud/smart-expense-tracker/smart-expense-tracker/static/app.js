const $ = (id) => document.getElementById(id);
const rupee = (n) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
let pie, bar;

async function api(url, options) {
  const res = await fetch(url, options);
  return res.json();
}

function drawCharts(s) {
  if (typeof Chart === "undefined") return; // offline: skip charts, rest still works
  const colors = ["#4f46e5", "#06b6d4", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6", "#ec4899", "#64748b"];
  if (pie) pie.destroy();
  if (bar) bar.destroy();
  pie = new Chart($("pie"), {
    type: "doughnut",
    data: { labels: s.by_category.map((c) => c.category),
            datasets: [{ data: s.by_category.map((c) => c.total), backgroundColor: colors }] },
  });
  bar = new Chart($("bar"), {
    type: "bar",
    data: { labels: s.by_day.map((d) => d.day.slice(8)),
            datasets: [{ label: "₹ per day", data: s.by_day.map((d) => d.total), backgroundColor: "#4f46e5" }] },
    options: { plugins: { legend: { display: false } } },
  });
}

async function refresh() {
  const s = await api("/api/summary");
  $("total").textContent = rupee(s.total);
  $("budget").textContent = rupee(s.budget);
  $("forecast").textContent = rupee(s.forecast);
  $("percent").textContent = s.percent_used + "%";
  const box = $("alert");
  box.textContent = s.alert;
  box.className = "alert" + (s.alert.startsWith("Over") ? " bad" : s.alert.startsWith("You are") ? "" : " warn");
  drawCharts(s);

  const rows = await api("/api/expenses");
  $("rows").innerHTML = rows.slice(0, 30).map((r) =>
    `<tr><td>${r.spent_on}</td><td>${escapeHtml(r.description)}</td><td>${r.category}</td>` +
    `<td>${rupee(r.amount)}</td><td><button class="del" data-id="${r.id}">Delete</button></td></tr>`).join("");
}

function escapeHtml(t) {
  return t.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("expense-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    description: $("description").value,
    amount: $("amount").value,
    category: $("category").value,
    spent_on: $("spent_on").value,
  };
  const res = await api("/api/expenses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (res.error) return alert(res.error);
  $("description").value = "";
  $("amount").value = "";
  refresh();
});

$("rows").addEventListener("click", async (e) => {
  const id = e.target.dataset.id;
  if (id) { await api("/api/expenses/" + id, { method: "DELETE" }); refresh(); }
});

$("set-budget").addEventListener("click", async () => {
  const res = await api("/api/budget", { method: "POST", headers: { "Content-Type": "application/json" },
                                          body: JSON.stringify({ budget: $("budget-input").value }) });
  if (res.error) return alert(res.error);
  $("budget-input").value = "";
  refresh();
});

$("backup").addEventListener("click", async () => {
  const res = await api("/api/backup", { method: "POST" });
  $("backup-msg").textContent = res.result;
});

refresh();
