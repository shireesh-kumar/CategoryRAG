let selectedCategoryId = null;
let pollTimer = null;

const messageEl = () => document.getElementById("message");

function showMessage(text, isError = false) {
  const el = messageEl();
  if (!el) return;
  el.textContent = text;
  el.className = isError ? "message message-error" : "message message-info";
  el.classList.remove("hidden");
}

function clearMessage() {
  const el = messageEl();
  if (!el) return;
  el.classList.add("hidden");
  el.textContent = "";
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg =
      body.details?.message ||
      body.details?.field ||
      body.error ||
      response.statusText;
    throw new Error(msg);
  }
  return body;
}

function renderCategories(categories) {
  const list = document.getElementById("category-list");
  const template = document.getElementById("category-item-template");
  list.innerHTML = "";

  if (!categories.length) {
    list.innerHTML = '<li class="empty-state">No categories yet.</li>';
    return;
  }

  for (const category of categories) {
    const node = template.content.cloneNode(true);
    const item = node.querySelector(".list-item");
    item.dataset.categoryId = category.id;
    if (category.id === selectedCategoryId) {
      item.classList.add("selected");
    }
    item.querySelector(".list-item-title").textContent = category.name;
    item.querySelector(".list-item-meta").textContent = category.description || category.id;
    item.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      selectCategory(category.id, category.name);
    });
    item.querySelector(".btn-delete-category").addEventListener("click", (event) => {
      event.stopPropagation();
      deleteCategory(category.id);
    });
    list.appendChild(node);
  }
}

async function loadCategories() {
  const categories = await apiJson("/categories");
  renderCategories(categories);
}

function renderDocuments(documents) {
  const list = document.getElementById("document-list");
  const template = document.getElementById("document-item-template");
  list.innerHTML = "";

  if (!documents.length) {
    list.innerHTML = '<li class="empty-state">No documents in this category.</li>';
    return;
  }

  for (const doc of documents) {
    const node = template.content.cloneNode(true);
    const item = node.querySelector(".list-item");
    item.dataset.documentId = doc.id;
    item.querySelector(".list-item-title").textContent = doc.filename;
    const status = item.querySelector(".status");
    status.textContent = doc.status;
    status.className = `status status-${doc.status}`;
    const errorEl = item.querySelector(".doc-error");
    errorEl.textContent = doc.error ? ` — ${doc.error}` : "";
    item.querySelector(".btn-delete-document").addEventListener("click", () => {
      deleteDocument(doc.id);
    });
    list.appendChild(node);
  }
}

async function loadDocuments() {
  if (!selectedCategoryId) return;
  const documents = await apiJson(`/categories/${selectedCategoryId}/documents`);
  renderDocuments(documents);
  schedulePoll(documents);
}

function schedulePoll(documents) {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  const active = documents.some((doc) =>
    ["pending", "processing"].includes(doc.status),
  );
  if (active) {
    pollTimer = setInterval(loadDocuments, 3000);
  }
}

async function selectCategory(id, name) {
  selectedCategoryId = id;
  document.getElementById("documents-content").classList.remove("hidden");
  document.getElementById("search-panel").classList.remove("hidden");
  document.getElementById("documents-subtitle").textContent = `Category: ${name}`;
  document.getElementById("search-results").innerHTML = "";
  await loadCategories();
  await loadDocuments();
}

async function deleteCategory(id) {
  if (!confirm("Delete this category and all documents?")) return;
  try {
    const response = await fetch(`/categories/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed");
    if (selectedCategoryId === id) {
      selectedCategoryId = null;
      document.getElementById("documents-content").classList.add("hidden");
      document.getElementById("search-panel").classList.add("hidden");
    }
    clearMessage();
    await loadCategories();
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function deleteDocument(id) {
  if (!confirm("Delete this document?")) return;
  try {
    const response = await fetch(
      `/categories/${selectedCategoryId}/documents/${id}`,
      { method: "DELETE" },
    );
    if (!response.ok) throw new Error("Delete failed");
    clearMessage();
    await loadDocuments();
  } catch (err) {
    showMessage(err.message, true);
  }
}

document.getElementById("create-category-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();
  const name = document.getElementById("category-name").value.trim();
  const description = document.getElementById("category-description").value.trim();
  try {
    await apiJson("/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    document.getElementById("create-category-form").reset();
    showMessage("Category created.");
    await loadCategories();
  } catch (err) {
    showMessage(err.message, true);
  }
});

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedCategoryId) return;
  clearMessage();
  const input = document.getElementById("file-input");
  if (!input.files.length) {
    showMessage("Choose at least one file.", true);
    return;
  }
  const formData = new FormData();
  for (const file of input.files) {
    formData.append("file", file);
  }
  try {
    const response = await fetch(`/categories/${selectedCategoryId}/documents`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.details?.message || body.error || "Upload failed");
    }
    input.value = "";
    showMessage("Upload accepted. Processing in background.");
    await loadDocuments();
  } catch (err) {
    showMessage(err.message, true);
  }
});

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedCategoryId) return;
  clearMessage();
  const query = document.getElementById("search-query").value.trim();
  try {
    const results = await apiJson(`/categories/${selectedCategoryId}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    const container = document.getElementById("search-results");
    const template = document.getElementById("search-result-template");
    container.innerHTML = "";
    if (!results.length) {
      container.innerHTML = '<p class="empty-state">No results.</p>';
      return;
    }
    for (const result of results) {
      const node = template.content.cloneNode(true);
      node.querySelector("h4").textContent = result.filename || "Match";
      node.querySelector(".result-score").textContent = `Score: ${result.score?.toFixed(3) ?? ""}`;
      node.querySelector(".result-text").textContent = result.text || "";
      container.appendChild(node);
    }
  } catch (err) {
    showMessage(err.message, true);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  loadCategories().catch((err) => showMessage(err.message, true));
});
