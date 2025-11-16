import "./styles.css";

const state = {
  items: [],
  page: 1,
  pageSize: 20,
  total: 0,
};

const PROMPT_PREVIEW_LIMIT = 160;
let capturedAtDirty = false;

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function serializeTagsInput(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function renderTags(container, tags) {
  container.innerHTML = "";
  tags.forEach((tag) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag.name;
    container.appendChild(span);
  });
}

function openModal(id) {
  document.getElementById(id).hidden = false;
  document.addEventListener("keydown", handleEscape);
}

function closeModal(id) {
  document.getElementById(id).hidden = true;
  document.removeEventListener("keydown", handleEscape);
}

function handleEscape(event) {
  if (event.key === "Escape") {
    let closed = false;
    document.querySelectorAll(".modal").forEach((modal) => {
      if (!modal.hidden) {
        modal.hidden = true;
        closed = true;
      }
    });
    if (closed) {
      event.preventDefault();
    }
  }
}

function truncatePrompt(text) {
  if (!text) {
    return "";
  }
  if (text.length <= PROMPT_PREVIEW_LIMIT) {
    return text;
  }
  return `${text.slice(0, PROMPT_PREVIEW_LIMIT)}…`;
}

function renderCards(items) {
  state.items = items;
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = "";
  const template = document.getElementById("image-card-template");

  items.forEach((item) => {
    const fragment = template.content.cloneNode(true);
    const imageEl = fragment.querySelector("[data-image]");
    imageEl.src = `/images/${item.file_name}`;
    imageEl.alt = item.prompt_text;
    imageEl.addEventListener("click", () => openDetailModal(item.id));

    const promptEl = fragment.querySelector("[data-prompt]");
    promptEl.textContent = truncatePrompt(item.prompt_text);
    promptEl.title = item.prompt_text;

    fragment.querySelector("[data-model]").textContent = item.ai_model
      ? `Model: ${item.ai_model}`
      : "Model unknown";
    renderTags(fragment.querySelector("[data-tags]"), item.tags);
    fragment.querySelector("[data-edit-button]").addEventListener("click", () => openEditModal(item.id));
    gallery.appendChild(fragment);
  });
}

function renderPagination() {
  const indicator = document.getElementById("pageIndicator");
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  indicator.textContent = `Page ${state.page} / ${totalPages}`;
  document.getElementById("prevPage").disabled = state.page <= 1;
  document.getElementById("nextPage").disabled = state.page >= totalPages;
}

async function refreshGallery(resetPage = false) {
  if (resetPage) {
    state.page = 1;
  }
  const params = new URLSearchParams();
  const query = document.getElementById("searchInput").value.trim();
  const tags = Array.from(document.getElementById("tagFilter").selectedOptions).map((option) => option.value);
  const ratingMin = document.getElementById("ratingMin").value;
  const ratingMax = document.getElementById("ratingMax").value;
  const dateFrom = document.getElementById("dateFrom").value;
  const dateTo = document.getElementById("dateTo").value;

  if (query) params.set("q", query);
  if (tags.length) params.set("tags", tags.join(","));
  if (ratingMin) params.set("rating_min", ratingMin);
  if (ratingMax) params.set("rating_max", ratingMax);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  params.set("page", String(state.page));
  params.set("page_size", String(state.pageSize));

  const { items, total } = await fetchJSON(`/api/images?${params.toString()}`);
  state.total = total;
  renderCards(items);
  renderPagination();
}

async function populateTags() {
  const tags = await fetchJSON("/api/tags");
  const select = document.getElementById("tagFilter");
  select.innerHTML = "";
  tags.forEach((tag) => {
    const option = document.createElement("option");
    option.value = tag.name;
    option.textContent = `${tag.name} (${tag.count})`;
    select.appendChild(option);
  });
  updateTagSummary();
}

function updateTagSummary() {
  const select = document.getElementById("tagFilter");
  const summary = document.getElementById("tagFilterSummary");
  const selected = Array.from(select.selectedOptions);
  if (!summary) {
    return;
  }
  if (!selected.length) {
    summary.textContent = "Tags";
  } else {
    summary.textContent = `Tags (${selected.length})`;
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const tags = serializeTagsInput(formData.get("tags") || "");
  formData.set("tags", JSON.stringify(tags));

  try {
    const response = await fetch("/api/images", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("Upload failed");
    }
    form.reset();
    closeModal("uploadModal");
    await populateTags();
    await refreshGallery(true);
    updateTagSummary();
    capturedAtDirty = false;
  } catch (error) {
    alert(error.message);
  }
}

function openEditModal(imageId) {
  const image = state.items.find((item) => item.id === imageId);
  if (!image) return;
  document.getElementById("editImageId").value = image.id;
  document.getElementById("editPrompt").value = image.prompt_text;
  document.getElementById("editTags").value = image.tags.map((tag) => tag.name).join(", ");
  document.getElementById("editModel").value = image.ai_model || "";
  document.getElementById("editNotes").value = image.notes || "";
  document.getElementById("editRating").value = image.rating ?? "";
  openModal("editModal");
}

async function handleEdit(event) {
  event.preventDefault();
  const id = document.getElementById("editImageId").value;
  const payload = {
    prompt_text: document.getElementById("editPrompt").value,
    tags: serializeTagsInput(document.getElementById("editTags").value),
    ai_model: document.getElementById("editModel").value || null,
    notes: document.getElementById("editNotes").value || null,
    rating: document.getElementById("editRating").value ? Number(document.getElementById("editRating").value) : null,
  };

  try {
    const response = await fetch(`/api/images/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("Update failed");
    }
    closeModal("editModal");
    await populateTags();
    await refreshGallery();
    updateTagSummary();
  } catch (error) {
    alert(error.message);
  }
}

function openDetailModal(imageId) {
  const image = state.items.find((item) => item.id === imageId);
  if (!image) return;
  const imageEl = document.getElementById("detailImage");
  imageEl.src = `/images/${image.file_name}`;
  imageEl.alt = image.prompt_text;
  document.getElementById("detailPrompt").textContent = image.prompt_text;
  document.getElementById("detailModel").textContent = image.ai_model || "Unknown";
  document.getElementById("detailRating").textContent =
    typeof image.rating === "number" ? `${image.rating}/5` : "Unrated";
  document.getElementById("detailNotes").textContent = image.notes || "None";
  const tagContainer = document.getElementById("detailTags");
  renderTags(tagContainer, image.tags);
  openModal("detailModal");
}

function wireEvents() {
  document.getElementById("refreshButton").addEventListener("click", () => refreshGallery(true));
  document.getElementById("clearFiltersButton").addEventListener("click", clearFilters);
  document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      refreshGallery(true);
    }
  });
  document.getElementById("addImageButton").addEventListener("click", () => openModal("uploadModal"));
  document.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", (event) => closeModal(event.currentTarget.dataset.closeModal));
  });
  document.getElementById("uploadForm").addEventListener("submit", handleUpload);
  document.getElementById("editForm").addEventListener("submit", handleEdit);
  document.getElementById("prevPage").addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      refreshGallery();
    }
  });
  document.getElementById("nextPage").addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
    if (state.page < totalPages) {
      state.page += 1;
      refreshGallery();
    }
  });
  document.getElementById("tagFilter").addEventListener("change", updateTagSummary);
  const fileInput = document.querySelector('input[name="image_file"]');
  const capturedInput = document.querySelector('input[name="captured_at"]');
  if (capturedInput) {
    capturedInput.addEventListener("input", () => {
      capturedAtDirty = true;
    });
  }
  if (fileInput && capturedInput) {
    fileInput.addEventListener("change", () => {
      if (capturedAtDirty) {
        return;
      }
      const fileName = fileInput.files?.[0]?.name;
      const guessed = extractDateFromFilename(fileName);
      if (guessed) {
        capturedInput.value = guessed;
      }
    });
  }
  setupTagFilterCollapse();
}

async function bootstrap() {
  wireEvents();
  await populateTags();
  await refreshGallery();
}

bootstrap().catch((error) => {
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = `<p class="error">Failed to load gallery: ${error.message}</p>`;
});

function clearFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("ratingMin").value = "";
  document.getElementById("ratingMax").value = "";
  document.getElementById("dateFrom").value = "";
  document.getElementById("dateTo").value = "";
  const tagSelect = document.getElementById("tagFilter");
  Array.from(tagSelect.options).forEach((option) => {
    option.selected = false;
  });
  updateTagSummary();
  refreshGallery(true);
}

function extractDateFromFilename(filename = "") {
  if (!filename) return null;
  const base = filename.split(".")[0];
  const isoMatch = base.match(
    /(\d{4})[-_]?(\d{2})[-_]?(\d{2})(?:[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2}))?/
  );
  if (isoMatch) {
    const [, year, month, day, hour = "00", minute = "00", second = "00"] = isoMatch;
    const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second)));
    return formatDateForInput(date);
  }
  const unixMatch = base.match(/(\d{10,})/);
  if (unixMatch) {
    const raw = unixMatch[1];
    const timestamp =
      raw.length > 10 ? Number(raw) / 10 ** (raw.length - 10) : Number(raw);
    if (!Number.isNaN(timestamp)) {
      const date = new Date(timestamp * 1000);
      return formatDateForInput(date);
    }
  }
  return null;
}

function formatDateForInput(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return null;
  }
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function setupTagFilterCollapse() {
  const tagFilter = document.querySelector(".tag-filter");
  if (!tagFilter) {
    return;
  }
  document.addEventListener("click", (event) => {
    if (!tagFilter.contains(event.target)) {
      tagFilter.removeAttribute("open");
    }
  });
}
