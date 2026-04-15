(function () {
  const apiRoot = "/api";

  function getCookie(name) {
    const cookieValue = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : null;
  }

  const csrfToken = () => getCookie("csrftoken");

  async function request(url, options) {
    const config = {
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    };

    if (["POST", "PUT", "PATCH", "DELETE"].includes((config.method || "GET").toUpperCase())) {
      config.headers["X-CSRFToken"] = csrfToken();
    }

    const response = await fetch(url, config);
    if (!response.ok) {
      let error = "Request failed";
      try {
        const data = await response.json();
        error = data.detail || JSON.stringify(data);
      } catch (_error) {
        error = response.statusText;
      }
      throw new Error(error);
    }

    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  function renderPagination(containerId, currentPage, hasNext, onPageChange) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = "";

    const prev = document.createElement("button");
    prev.className = "btn-secondary";
    prev.textContent = "Prev";
    prev.disabled = currentPage <= 1;
    prev.onclick = function () {
      if (currentPage > 1) onPageChange(currentPage - 1);
    };

    const pageLabel = document.createElement("span");
    pageLabel.textContent = `Page ${currentPage}`;
    pageLabel.className = "px-3 py-2 text-sm";

    const next = document.createElement("button");
    next.className = "btn-secondary";
    next.textContent = "Next";
    next.disabled = !hasNext;
    next.onclick = function () {
      if (hasNext) onPageChange(currentPage + 1);
    };

    el.appendChild(prev);
    el.appendChild(pageLabel);
    el.appendChild(next);
  }

  const state = {
    productPage: 1,
    txPage: 1,
    chart: null,
  };

  function currentAccess() {
    const body = document.body.dataset || {};
    return {
      canManageInventory: body.canManageInventory === "true",
      canManageEmployees: body.canManageEmployees === "true",
      isOwner: body.isOwner === "true",
    };
  }

  function formatCurrency(value) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(Number(value || 0));
  }

  function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getProductStatus(product) {
    if (product.is_low_stock) {
      return { label: "Low stock", className: "status-pill status-pill-danger" };
    }
    if (Number(product.quantity) === 0) {
      return { label: "Out of stock", className: "status-pill status-pill-muted" };
    }
    return { label: "Healthy", className: "status-pill status-pill-good" };
  }

  function getSupplierStatus(supplier) {
    if (supplier.email && supplier.phone && supplier.contact_person) {
      return { label: "Complete", className: "status-pill status-pill-good" };
    }
    if (supplier.email || supplier.phone || supplier.contact_person) {
      return { label: "Partial", className: "status-pill status-pill-danger" };
    }
    return { label: "Basic", className: "status-pill status-pill-muted" };
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value;
    }
  }

  function toggleComposer(composerId, toggleId, openLabel, closeLabel, forceVisible) {
    const composer = document.getElementById(composerId);
    const toggle = document.getElementById(toggleId);
    if (!composer) return;

    const willShow = typeof forceVisible === "boolean" ? forceVisible : composer.classList.contains("hidden");
    composer.classList.toggle("hidden", !willShow);
    composer.classList.toggle("composer-open", willShow);

    if (toggle) {
      toggle.textContent = willShow ? closeLabel : openLabel;
    }

    if (willShow) {
      composer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function toggleProductComposer(forceVisible) {
    toggleComposer("productComposer", "productComposerToggle", "Add Product", "Hide Product Form", forceVisible);
  }

  function toggleSupplierComposer(forceVisible) {
    toggleComposer("supplierComposer", "supplierComposerToggle", "Add Supplier", "Hide Supplier Form", forceVisible);
  }

  function toggleTransactionComposer(forceVisible) {
    toggleComposer("transactionComposer", "transactionComposerToggle", "Record Transaction", "Hide Transaction Form", forceVisible);
  }

  function bindToggle(id, callback) {
    const toggle = document.getElementById(id);
    if (!toggle || toggle.dataset.bound === "true") return;
    toggle.dataset.bound = "true";
    toggle.addEventListener("click", callback);
  }

  function bindComposerToggle() {
    bindToggle("productComposerToggle", function () {
      const id = document.getElementById("productId");
      if (id && id.value) {
        resetProductForm();
        return;
      }
      toggleProductComposer();
    });
  }

  function bindInventoryFilters() {
    const search = document.getElementById("productSearch");
    const stockFilter = document.getElementById("productStockFilter");
    if (search && search.dataset.bound !== "true") {
      search.dataset.bound = "true";
      search.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          loadProducts(1);
        }
      });
      search.addEventListener("change", function () {
        loadProducts(1);
      });
    }
    if (stockFilter && stockFilter.dataset.bound !== "true") {
      stockFilter.dataset.bound = "true";
      stockFilter.addEventListener("change", function () {
        loadProducts(1);
      });
    }
  }

  function bindSupplierComposerToggle() {
    bindToggle("supplierComposerToggle", function () {
      const id = document.getElementById("supplierId");
      if (id && id.value) {
        resetSupplierForm();
        return;
      }
      toggleSupplierComposer();
    });
  }

  function bindSupplierFilters() {
    const search = document.getElementById("supplierSearch");
    if (search && search.dataset.bound !== "true") {
      search.dataset.bound = "true";
      search.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          loadSuppliers();
        }
      });
      search.addEventListener("change", function () {
        loadSuppliers();
      });
    }
  }

  function bindTransactionComposerToggle() {
    bindToggle("transactionComposerToggle", function () {
      toggleTransactionComposer();
    });
  }

  function bindTransactionFilters() {
    const search = document.getElementById("transactionSearch");
    const filter = document.getElementById("transactionFilter");
    if (search && search.dataset.bound !== "true") {
      search.dataset.bound = "true";
      search.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          loadTransactions(1);
        }
      });
      search.addEventListener("change", function () {
        loadTransactions(1);
      });
    }
    if (filter && filter.dataset.bound !== "true") {
      filter.dataset.bound = "true";
      filter.addEventListener("change", function () {
        loadTransactions(1);
      });
    }
  }

  function initPasswordToggles(root) {
    const scope = root || document;
    const toggles = scope.querySelectorAll("[data-password-toggle]");

    toggles.forEach((toggle) => {
      if (toggle.dataset.bound === "true") return;

      const container = toggle.closest(".password-field");
      const input = container ? container.querySelector("input") : null;
      if (!input) return;

      toggle.dataset.bound = "true";
      input.dataset.passwordInput = "true";

      function syncState(isVisible) {
        container.classList.toggle("password-visible", isVisible);
        toggle.setAttribute("aria-label", isVisible ? "Hide password" : "Show password");
        toggle.setAttribute("aria-pressed", isVisible ? "true" : "false");
      }

      syncState(input.type === "text");

      toggle.addEventListener("click", function () {
        const shouldShow = input.type === "password";
        input.type = shouldShow ? "text" : "password";
        syncState(shouldShow);
      });
    });
  }

  async function fetchSuppliersSimple() {
    const data = await request(`${apiRoot}/suppliers/?page_size=200`);
    return data.results || data;
  }

  async function fetchProductsSimple() {
    const data = await request(`${apiRoot}/products/?page_size=200`);
    return data.results || data;
  }

  async function fetchLocationsSimple() {
    const data = await request(`${apiRoot}/locations/?page_size=200`);
    return data.results || data;
  }

  function updateInventoryMeta(data) {
    const meta = document.getElementById("inventoryResultsMeta");
    if (!meta) return;
    const count = (data.results || []).length;
    const search = document.getElementById("productSearch")?.value?.trim();
    const filter = document.getElementById("productStockFilter")?.value;
    let message = `Showing ${count} products on this page.`;
    if (filter === "low") {
      message = `Showing ${count} low-stock products that need attention.`;
    }
    if (search) {
      message += ` Search: ${search}.`;
    }
    meta.textContent = message;
  }

  function updateSupplierMeta(suppliers) {
    const search = document.getElementById("supplierSearch")?.value?.trim();
    let message = `Showing ${suppliers.length} suppliers in your directory.`;
    if (search) {
      message += ` Search: ${search}.`;
    }
    setText("suppliersResultsMeta", message);
  }

  function updateSupplierSummary(suppliers) {
    setText("totalSuppliers", suppliers.length);
    setText("suppliersWithEmail", suppliers.filter((supplier) => supplier.email).length);
    setText("suppliersWithPhone", suppliers.filter((supplier) => supplier.phone).length);
    setText("suppliersWithContact", suppliers.filter((supplier) => supplier.contact_person).length);
  }

  function updateTransactionMeta(data) {
    const count = (data.results || []).length;
    const search = document.getElementById("transactionSearch")?.value?.trim();
    const filter = document.getElementById("transactionFilter")?.value || "all";
    let message = `Showing ${count} transactions on this page.`;
    if (filter !== "all") {
      message = `Showing ${count} ${filter === "IN" ? "stock-in" : "stock-out"} transactions on this page.`;
    }
    if (search) {
      message += ` Search: ${search}.`;
    }
    setText("transactionsResultsMeta", message);
  }

  function renderProductRows(products) {
    const access = currentAccess();
    return products
      .map((product) => {
        const status = getProductStatus(product);
        const actions = access.canManageInventory
          ? `
              <button class="btn-secondary" data-edit-product="${encodeURIComponent(JSON.stringify(product))}">Edit</button>
              ${access.isOwner ? `<button class="btn-danger" data-delete-product="${product.id}">Delete</button>` : ""}
            `
          : `<span class="text-slate-500">View only</span>`;
        return `
          <tr class="border-b border-slate-800/80">
            <td class="py-3">
              <div class="font-semibold text-slate-50">${escapeHtml(product.name)}</div>
              <div class="text-xs text-slate-400">${formatCurrency(product.price)} each • ${escapeHtml(product.location_name || "No location")}</div>
            </td>
            <td class="py-3">${escapeHtml(product.sku || "-")}</td>
            <td class="py-3">${escapeHtml(product.category)}</td>
            <td class="py-3 ${product.is_low_stock ? "text-amber-200 font-semibold" : "text-slate-100"}">${escapeHtml(product.quantity)}</td>
            <td class="py-3">${escapeHtml(product.supplier_name || "-")}</td>
            <td class="py-3"><span class="${status.className}">${status.label}</span></td>
            <td class="py-3 space-x-2">${actions}</td>
          </tr>
        `;
      })
      .join("");
  }

  function bindProductTableActions() {
    const tbody = document.getElementById("productsTable");
    if (!tbody || tbody.dataset.bound === "true") return;
    tbody.dataset.bound = "true";
    tbody.addEventListener("click", function (event) {
      const editButton = event.target.closest("[data-edit-product]");
      if (editButton) {
        editProduct(JSON.parse(decodeURIComponent(editButton.dataset.editProduct)));
        return;
      }
      const deleteButton = event.target.closest("[data-delete-product]");
      if (deleteButton) {
        deleteProduct(deleteButton.dataset.deleteProduct);
      }
    });
  }

  function bindSupplierTableActions() {
    const tbody = document.getElementById("suppliersTable");
    if (!tbody || tbody.dataset.bound === "true") return;
    tbody.dataset.bound = "true";
    tbody.addEventListener("click", function (event) {
      const editButton = event.target.closest("[data-edit-supplier]");
      if (editButton) {
        editSupplier(JSON.parse(decodeURIComponent(editButton.dataset.editSupplier)));
        return;
      }
      const deleteButton = event.target.closest("[data-delete-supplier]");
      if (deleteButton) {
        deleteSupplier(deleteButton.dataset.deleteSupplier);
      }
    });
  }

  async function initDashboard() {
    const data = await request(`${apiRoot}/dashboard/summary/`);
    setText("totalProducts", data.total_products);
    setText("lowStockItems", data.low_stock_items);
    setText("totalTransactions", data.total_transactions);
    setText("activeSuppliers", data.active_suppliers);
    setText("totalEmployees", data.total_employees);
    setText("totalUnits", data.total_units);
    setText("inventoryValue", formatCurrency(data.inventory_value));

    const lowStockList = document.getElementById("lowStockList");
    if (lowStockList) {
      lowStockList.innerHTML = "";
      if ((data.low_stock_products || []).length === 0) {
        lowStockList.innerHTML = "<li class='text-slate-300'>No low-stock items.</li>";
      } else {
        data.low_stock_products.forEach((item) => {
          const li = document.createElement("li");
          li.className = "alert-row";
          li.innerHTML = `<strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.quantity)}/${escapeHtml(item.reorder_level)} left</span>`;
          lowStockList.appendChild(li);
        });
      }
    }

    const tbody = document.getElementById("recentTransactionsTable");
    if (tbody) {
      tbody.innerHTML = (data.recent_transactions || [])
        .map(
          (tx) => `
            <tr class="border-b border-slate-800">
              <td class="py-2">${escapeHtml(tx.product_name)}</td>
              <td class="py-2">${escapeHtml(tx.transaction_type)}</td>
              <td class="py-2">${escapeHtml(tx.quantity)}</td>
              <td class="py-2">${escapeHtml(tx.performed_by_username || "-")}</td>
              <td class="py-2">${formatDate(tx.created_at)}</td>
            </tr>
          `,
        )
        .join("");
    }

    const activityList = document.getElementById("recentActivityList");
    if (activityList) {
      activityList.innerHTML = (data.recent_activity || []).length
        ? (data.recent_activity || [])
            .map(
              (item) => `<li class="feature-row"><strong>${escapeHtml(item.action)}</strong><div class="text-xs text-slate-400 mt-1">${escapeHtml(item.description || item.entity_type || "Activity recorded")} • ${escapeHtml(item.actor || "system")} • ${formatDate(item.created_at)}</div></li>`,
            )
            .join("")
        : "<li class='text-slate-300'>No recent activity yet.</li>";
    }

    const notificationList = document.getElementById("notificationList");
    if (notificationList) {
      notificationList.innerHTML = (data.notifications || []).length
        ? (data.notifications || [])
            .map(
              (item) => `<li class="feature-row"><strong>${escapeHtml(item.title)}</strong><div class="text-xs text-slate-400 mt-1">${escapeHtml(item.message)} • ${formatDate(item.created_at)}</div></li>`,
            )
            .join("")
        : "<li class='text-slate-300'>No unread notifications.</li>";
    }

    const labels = (data.category_distribution || []).map((item) => item.category);
    const values = (data.category_distribution || []).map((item) => item.total);
    const chartCtx = document.getElementById("categoryChart");
    if (chartCtx) {
      if (state.chart) {
        state.chart.destroy();
      }
      state.chart = new Chart(chartCtx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Products",
              data: values,
              backgroundColor: ["#06b6d4", "#0ea5e9", "#f97316", "#84cc16", "#a855f7"],
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: "#e2e8f0" } } },
          scales: {
            x: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(100,116,139,0.25)" } },
            y: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(100,116,139,0.25)" } },
          },
        },
      });
    }

    await initInventory();
  }

  function resetProductForm() {
    const form = document.getElementById("productForm");
    if (form) form.reset();
    if (document.getElementById("productId")) document.getElementById("productId").value = "";
    setText("productComposerTitle", "Add Product");
    toggleProductComposer(false);
  }

  async function loadProducts(page) {
    state.productPage = page || state.productPage;
    const search = document.getElementById("productSearch")?.value || "";
    const stockFilter = document.getElementById("productStockFilter")?.value || "all";
    const query = new URLSearchParams({ page: state.productPage });
    if (search) query.set("search", search);
    if (stockFilter === "low") query.set("low_stock", "true");

    const data = await request(`${apiRoot}/products/?${query.toString()}`);
    const tbody = document.getElementById("productsTable");
    if (tbody) tbody.innerHTML = renderProductRows(data.results || []);
    bindProductTableActions();
    updateInventoryMeta(data);
    renderPagination("productsPagination", state.productPage, Boolean(data.next), loadProducts);
  }

  async function saveProduct(event) {
    event.preventDefault();
    const id = document.getElementById("productId")?.value;
    const payload = {
      name: document.getElementById("productName").value,
      sku: document.getElementById("productSku").value,
      category: document.getElementById("productCategory").value,
      quantity: Number(document.getElementById("productQuantity").value),
      price: document.getElementById("productPrice").value,
      reorder_level: Number(document.getElementById("productReorder").value),
      location: document.getElementById("productLocation")?.value || null,
      supplier: document.getElementById("productSupplier")?.value || null,
      is_active: true,
    };

    if (id) {
      await request(`${apiRoot}/products/${id}/`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await request(`${apiRoot}/products/`, { method: "POST", body: JSON.stringify(payload) });
    }
    resetProductForm();
    await loadProducts(1);
    if (document.body.dataset.page === "dashboard") {
      await initDashboard();
    }
  }

  function editProduct(product) {
    document.getElementById("productId").value = product.id;
    document.getElementById("productName").value = product.name;
    document.getElementById("productSku").value = product.sku || "";
    document.getElementById("productCategory").value = product.category;
    document.getElementById("productQuantity").value = product.quantity;
    document.getElementById("productPrice").value = product.price;
    document.getElementById("productReorder").value = product.reorder_level;
    if (document.getElementById("productLocation")) document.getElementById("productLocation").value = product.location || "";
    if (document.getElementById("productSupplier")) document.getElementById("productSupplier").value = product.supplier || "";
    setText("productComposerTitle", `Edit ${product.name}`);
    toggleProductComposer(true);
  }

  async function deleteProduct(id) {
    if (!confirm("Delete this product?")) return;
    await request(`${apiRoot}/products/${id}/`, { method: "DELETE" });
    await loadProducts(state.productPage);
    if (document.body.dataset.page === "dashboard") {
      await initDashboard();
    }
  }

  async function initInventory() {
    const [suppliers, locations] = await Promise.all([fetchSuppliersSimple(), fetchLocationsSimple()]);
    const supplierSelect = document.getElementById("productSupplier");
    const locationSelect = document.getElementById("productLocation");
    if (supplierSelect) {
      supplierSelect.innerHTML = `<option value="">No Supplier</option>`;
      suppliers.forEach((supplier) => {
        supplierSelect.innerHTML += `<option value="${supplier.id}">${escapeHtml(supplier.name)}</option>`;
      });
    }
    if (locationSelect) {
      locationSelect.innerHTML = `<option value="">Default Location</option>`;
      locations.forEach((location) => {
        locationSelect.innerHTML += `<option value="${location.id}">${escapeHtml(location.name)} (${escapeHtml(location.code)})</option>`;
      });
    }
    const productForm = document.getElementById("productForm");
    if (productForm && productForm.dataset.bound !== "true") {
      productForm.dataset.bound = "true";
      productForm.addEventListener("submit", saveProduct);
    }
    bindComposerToggle();
    bindInventoryFilters();
    await loadProducts(1);
  }

  function resetSupplierForm() {
    const form = document.getElementById("supplierForm");
    if (form) form.reset();
    if (document.getElementById("supplierId")) document.getElementById("supplierId").value = "";
    setText("supplierComposerTitle", "Add Supplier");
    toggleSupplierComposer(false);
  }

  async function loadSuppliers() {
    const search = document.getElementById("supplierSearch")?.value || "";
    const query = new URLSearchParams({ page_size: 200 });
    if (search) query.set("search", search);
    const data = await request(`${apiRoot}/suppliers/?${query.toString()}`);
    const suppliers = data.results || data;
    const access = currentAccess();
    const tbody = document.getElementById("suppliersTable");
    if (tbody) {
      tbody.innerHTML = suppliers
        .map((supplier) => {
          const status = getSupplierStatus(supplier);
          const actions = access.isOwner
            ? `<button class="btn-secondary" data-edit-supplier="${encodeURIComponent(JSON.stringify(supplier))}">Edit</button><button class="btn-danger" data-delete-supplier="${supplier.id}">Delete</button>`
            : `<span class="text-slate-500">Owner only</span>`;
          return `
            <tr class="border-b border-slate-800/80">
              <td class="py-3">
                <div class="font-semibold text-slate-50">${escapeHtml(supplier.name)}</div>
                <div class="text-xs text-slate-400">${escapeHtml(supplier.address || "No address saved")}</div>
              </td>
              <td class="py-3">${escapeHtml(supplier.contact_person || "-")}</td>
              <td class="py-3">${escapeHtml(supplier.email || "-")}</td>
              <td class="py-3">${escapeHtml(supplier.phone || "-")}</td>
              <td class="py-3"><span class="${status.className}">${status.label}</span></td>
              <td class="py-3 space-x-2">${actions}</td>
            </tr>
          `;
        })
        .join("");
    }
    bindSupplierTableActions();
    updateSupplierSummary(suppliers);
    updateSupplierMeta(suppliers);
  }

  async function saveSupplier(event) {
    event.preventDefault();
    const id = document.getElementById("supplierId").value;
    const payload = {
      name: document.getElementById("supplierName").value,
      contact_person: document.getElementById("supplierContact").value,
      email: document.getElementById("supplierEmail").value,
      phone: document.getElementById("supplierPhone").value,
      address: document.getElementById("supplierAddress").value,
    };
    if (id) {
      await request(`${apiRoot}/suppliers/${id}/`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await request(`${apiRoot}/suppliers/`, { method: "POST", body: JSON.stringify(payload) });
    }
    resetSupplierForm();
    await loadSuppliers();
  }

  function editSupplier(supplier) {
    document.getElementById("supplierId").value = supplier.id;
    document.getElementById("supplierName").value = supplier.name;
    document.getElementById("supplierContact").value = supplier.contact_person || "";
    document.getElementById("supplierEmail").value = supplier.email || "";
    document.getElementById("supplierPhone").value = supplier.phone || "";
    document.getElementById("supplierAddress").value = supplier.address || "";
    setText("supplierComposerTitle", `Edit ${supplier.name}`);
    toggleSupplierComposer(true);
  }

  async function deleteSupplier(id) {
    if (!confirm("Delete this supplier?")) return;
    await request(`${apiRoot}/suppliers/${id}/`, { method: "DELETE" });
    await loadSuppliers();
  }

  async function initSuppliers() {
    const supplierForm = document.getElementById("supplierForm");
    if (supplierForm && supplierForm.dataset.bound !== "true") {
      supplierForm.dataset.bound = "true";
      supplierForm.addEventListener("submit", saveSupplier);
    }
    bindSupplierComposerToggle();
    bindSupplierFilters();
    await loadSuppliers();
  }

  function resetTransactionForm() {
    const form = document.getElementById("transactionForm");
    if (form) form.reset();
    toggleTransactionComposer(false);
  }

  async function loadTransactionSummary() {
    const search = document.getElementById("transactionSearch")?.value || "";
    const filter = document.getElementById("transactionFilter")?.value || "all";
    const query = new URLSearchParams({ page_size: 200 });
    if (search) query.set("search", search);
    if (filter !== "all") query.set("type", filter);
    const data = await request(`${apiRoot}/transactions/?${query.toString()}`);
    const transactions = data.results || data;
    setText("totalTxRecords", transactions.length);
    setText("stockInCount", transactions.filter((tx) => tx.transaction_type === "IN").length);
    setText("stockOutCount", transactions.filter((tx) => tx.transaction_type === "OUT").length);
    setText("totalUnitsMoved", transactions.reduce((total, tx) => total + Number(tx.quantity || 0), 0));
  }

  async function loadTransactions(page) {
    state.txPage = page || state.txPage;
    const search = document.getElementById("transactionSearch")?.value || "";
    const filter = document.getElementById("transactionFilter")?.value || "all";
    const query = new URLSearchParams({ page: state.txPage });
    if (search) query.set("search", search);
    if (filter !== "all") query.set("type", filter);
    const data = await request(`${apiRoot}/transactions/?${query.toString()}`);
    const tbody = document.getElementById("transactionsTable");
    if (tbody) {
      tbody.innerHTML = (data.results || [])
        .map(
          (tx) => `
            <tr class="border-b border-slate-800/80">
              <td class="py-3 font-semibold text-slate-50">${escapeHtml(tx.product_name)}<div class="text-xs text-slate-400 mt-1">${escapeHtml(tx.location_name || "No location")}</div></td>
              <td class="py-3"><span class="${tx.transaction_type === "IN" ? "status-pill status-pill-good" : "status-pill status-pill-danger"}">${escapeHtml(tx.transaction_type)}</span></td>
              <td class="py-3">${escapeHtml(tx.quantity)}</td>
              <td class="py-3">${escapeHtml(tx.performed_by_username || "-")}</td>
              <td class="py-3">${formatDate(tx.created_at)}</td>
              <td class="py-3">${escapeHtml(tx.note || "-")}</td>
            </tr>
          `,
        )
        .join("");
    }
    updateTransactionMeta(data);
    await loadTransactionSummary();
    renderPagination("transactionsPagination", state.txPage, Boolean(data.next), loadTransactions);
  }

  async function saveTransaction(event) {
    event.preventDefault();
    const payload = {
      product: Number(document.getElementById("transactionProduct").value),
      location: document.getElementById("transactionLocation")?.value || null,
      transaction_type: document.getElementById("transactionType").value,
      quantity: Number(document.getElementById("transactionQuantity").value),
      note: document.getElementById("transactionNote").value,
    };
    await request(`${apiRoot}/transactions/`, { method: "POST", body: JSON.stringify(payload) });
    resetTransactionForm();
    await loadTransactions(1);
    if (document.body.dataset.page === "dashboard") {
      await initDashboard();
    }
  }

  async function initTransactions() {
    const [products, locations] = await Promise.all([fetchProductsSimple(), fetchLocationsSimple()]);
    const productSelect = document.getElementById("transactionProduct");
    const locationSelect = document.getElementById("transactionLocation");
    if (productSelect) {
      productSelect.innerHTML = "";
      products.forEach((product) => {
        productSelect.innerHTML += `<option value="${product.id}">${escapeHtml(product.name)} (${escapeHtml(product.sku || "-")})</option>`;
      });
    }
    if (locationSelect) {
      locationSelect.innerHTML = `<option value="">Use Product Default</option>`;
      locations.forEach((location) => {
        locationSelect.innerHTML += `<option value="${location.id}">${escapeHtml(location.name)} (${escapeHtml(location.code)})</option>`;
      });
    }
    const transactionForm = document.getElementById("transactionForm");
    if (transactionForm && transactionForm.dataset.bound !== "true") {
      transactionForm.dataset.bound = "true";
      transactionForm.addEventListener("submit", saveTransaction);
    }
    bindTransactionComposerToggle();
    bindTransactionFilters();
    await loadTransactions(1);
  }

  window.InventoryApp = {
    initDashboard,
    initInventory,
    initSuppliers,
    initTransactions,
    initPasswordToggles,
    loadProducts,
    resetProductForm,
    editProduct,
    deleteProduct,
    loadSuppliers,
    resetSupplierForm,
    editSupplier,
    deleteSupplier,
    loadTransactions,
    resetTransactionForm,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initPasswordToggles();
    });
  } else {
    initPasswordToggles();
  }
})();