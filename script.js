let monthlyChart = null;
let productChart = null;
let resultChart = null;

const money = value => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0
}).format(value || 0);

function makeChart(canvasId, labels, values, type, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const ctx = canvas.getContext("2d");
  return new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: "#2d887d",
        backgroundColor: type === "line" ? "rgba(45,136,125,.12)" : "rgba(45,136,125,.78)",
        borderWidth: type === "line" ? 2.5 : 0,
        fill: type === "line",
        tension: .32,
        borderRadius: type === "bar" ? 5 : 0,
        pointRadius: type === "line" ? 3 : 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#748394", font: { size: 10 } } },
        y: {
          beginAtZero: true,
          grid: { color: "#edf1f4" },
          ticks: { color: "#748394", font: { size: 10 }, callback: value => value >= 1000 ? `₹${value / 1000}k` : `₹${value}` }
        }
      }
    }
  });
}

async function loadDashboard() {
  const response = await fetch("/api/summary");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Unable to load dashboard.");

  document.getElementById("total-revenue").textContent = money(data.total_revenue);
  document.getElementById("transaction-count").textContent = data.transaction_count;
  document.getElementById("top-product").textContent = data.top_product;
  document.getElementById("top-product-revenue").textContent = money(data.top_product_revenue);
  document.getElementById("top-region").textContent = data.top_region;
  document.getElementById("top-region-revenue").textContent = money(data.top_region_revenue);
  document.getElementById("quality-note").textContent =
    `${data.data_quality.total_rows} rows · ${data.data_quality.flagged_rows} flagged`;

  monthlyChart?.destroy();
  monthlyChart = makeChart(
    "monthly-chart",
    data.monthly.map(row => row.month),
    data.monthly.map(row => row.revenue),
    "line", "Revenue"
  );
  productChart?.destroy();
  const topProducts = data.products.slice(0, 6).reverse();
  productChart = makeChart(
    "product-chart",
    topProducts.map(row => row.product),
    topProducts.map(row => row.revenue),
    "bar", "Revenue"
  );
}

function renderTable(rows) {
  const wrap = document.getElementById("result-table-wrap");
  if (!rows || !rows.length) {
    wrap.innerHTML = "";
    return;
  }
  const columns = Object.keys(rows[0]);
  const table = document.createElement("table");
  table.className = "result-table";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach(column => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach(row => {
    const tr = document.createElement("tr");
    columns.forEach(column => {
      const td = document.createElement("td");
      td.textContent = row[column] ?? "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.replaceChildren(table);
}

async function askQuestion(question) {
  const answerBox = document.getElementById("answer-box");
  const errorBox = document.getElementById("error-message");
  const button = document.getElementById("ask-button");
  answerBox.classList.add("hidden");
  errorBox.classList.add("hidden");
  button.disabled = true;
  button.textContent = "Working…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed.");
    if (!data.supported) throw new Error(data.message || "That question is not supported yet.");
    document.getElementById("answer-text").textContent = data.answer;
    renderTable(data.table);
    const chartWrap = document.querySelector(".result-chart-wrap");
    if (resultChart) { resultChart.destroy(); resultChart = null; }
    if (data.chart && data.chart.type !== "none" && data.chart.labels?.length) {
      chartWrap.classList.remove("hidden");
      resultChart = makeChart("result-chart", data.chart.labels, data.chart.values, data.chart.type, "Revenue");
    } else {
      chartWrap.classList.add("hidden");
    }
    answerBox.classList.remove("hidden");
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  } finally {
    button.disabled = false;
    button.innerHTML = 'Ask question <span>→</span>';
  }
}

document.getElementById("question-form").addEventListener("submit", event => {
  event.preventDefault();
  askQuestion(document.getElementById("question").value.trim());
});
document.querySelectorAll(".example-chip").forEach(button => {
  button.addEventListener("click", () => {
    const question = button.dataset.question;
    document.getElementById("question").value = question;
    askQuestion(question);
  });
});

loadDashboard().catch(error => {
  document.getElementById("quality-note").textContent = "Dataset could not load";
  document.getElementById("error-message").textContent = error.message;
  document.getElementById("error-message").classList.remove("hidden");
});
