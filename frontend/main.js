import "./styles.css";
import { extractDateFromFilename, formatDisplayDate } from "./dateUtils.js";
import { ReferencePicker } from "./referencePicker.js";
import { buildPromptMeta, shouldAutoFillThumbnail, getFirstReferenceAsset } from "./referenceUtils.js";
import { resetReferenceSearchState } from "./referenceSearchUtils.js";
import { computeStarFills } from "./ratingUtils.js";

const state = {
  items: [],
  page: 1,
  pageSize: 20,
  total: 0,
  detailCache: new Map(),
  thumbnailStyle: "landscape",
};

const PROMPT_PREVIEW_LIMIT = 160;
let capturedAtDirty = false;
let activeReferenceTarget = null;
const referenceSearchState = {
  page: 1,
  totalPages: 1,
  currentQuery: "",
};
const referencePickers = {};
const forms = {};
const THUMBNAIL_STYLE_KEY = "aiimglib:thumbnailStyle";
const DEFAULT_THUMBNAIL_STYLE = "landscape";
const REFERENCE_PAGE_SIZE = 8;

if (typeof window !== "undefined") {
  state.thumbnailStyle = localStorage.getItem(THUMBNAIL_STYLE_KEY) || DEFAULT_THUMBNAIL_STYLE;
}

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

function renderStars(container, rating) {
  container.innerHTML = "";
  const isNumber = typeof rating === "number";
  const fills = computeStarFills(isNumber ? rating : 0);
  fills.forEach((percent, index) => {
    const star = document.createElement("span");
    star.className = "star";
    const base = document.createElement("span");
    base.className = "star__base";
    base.textContent = "★";
    const fill = document.createElement("span");
    fill.className = "star__fill";
    fill.textContent = "★";
    fill.style.width = `${percent}%`;
    star.appendChild(base);
    star.appendChild(fill);
    container.appendChild(star);
  });
  if (!isNumber) {
    const label = document.createElement("span");
    label.className = "star__label";
    label.textContent = "Unrated";
    container.appendChild(label);
  }
  container.setAttribute("aria-label", isNumber ? `${rating} out of 5 stars` : "Unrated");
}

function openModal(id) {
  document.getElementById(id).hidden = false;
  document.addEventListener("keydown", handleEscape);
}

function closeModal(id) {
  document.getElementById(id).hidden = true;
  if (document.querySelectorAll(".modal:not([hidden])").length === 0) {
    document.removeEventListener("keydown", handleEscape);
  }
  if (id === "referenceModal") {
    activeReferenceTarget = null;
  }
}

function handleEscape(event) {
  if (event.key === "Escape") {
    const referenceModal = document.getElementById("referenceModal");
    if (referenceModal && !referenceModal.hidden) {
      closeModal("referenceModal");
      event.preventDefault();
      return;
    }
    document.querySelectorAll(".modal").forEach((modal) => {
      if (!modal.hidden) {
        closeModal(modal.id);
      }
    });
    event.preventDefault();
  }
}

function syncPromptMeta(key) {
  const formState = forms[key];
  if (!formState) return;
  const references = referencePickers[key]?.getReferences() ?? [];
  const promptValue = formState.promptInput?.value ?? "";
  const promptMeta = buildPromptMeta(promptValue, references);
  if (!formState.promptMetaInput) return;
  if (Array.isArray(promptMeta)) {
    formState.promptMetaInput.value = JSON.stringify(promptMeta);
  } else if (promptMeta === null) {
    formState.promptMetaInput.value = "";
  } else {
    formState.promptMetaInput.value = promptMeta;
  }
}

async function handleReferenceUpdate(key) {
  syncPromptMeta(key);
  await maybeAutoFillThumbnail(key);
}

async function maybeAutoFillThumbnail(key) {
  const formState = forms[key];
  if (!formState || !formState.thumbnailInput) return;
  if (formState.thumbnailDirty) return;
  if (formState.mediaTypeSelect.value !== "video") {
    formState.thumbnailInput.value = "";
    return;
  }
  const references = referencePickers[key]?.getReferences() ?? [];
  if (!shouldAutoFillThumbnail("video", references)) {
    return;
  }
  const asset = getFirstReferenceAsset(references);
  if (!asset) return;
  const source = asset.thumbnail || asset.file;
  if (!source) return;
  try {
    const response = await fetch(`/images/${source}`);
    if (!response.ok) return;
    const blob = await response.blob();
    const extension = source.includes(".") ? source.split(".").pop() : "png";
    const file = new File([blob], `reference-thumb-${Date.now()}.${extension}`, { type: blob.type || "image/png" });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    formState.thumbnailInput.files = transfer.files;
  } catch (error) {
    console.warn("Failed to auto-fill thumbnail", error);
  }
}

function openReferencePickerModal(target) {
  activeReferenceTarget = target;
  document.getElementById("referenceResults").innerHTML = "";
  document.getElementById("referenceSearchInput").value = "";
  resetReferenceSearchState(referenceSearchState, "");
  updateReferencePagination();
  openModal("referenceModal");
  fetchReferencePage(0);
}

async function performReferenceSearch() {
  if (!activeReferenceTarget) return;
  const query = document.getElementById("referenceSearchInput").value;
  resetReferenceSearchState(referenceSearchState, query);
  await fetchReferencePage(0);
}

async function fetchReferencePage(pageChange = 0) {
  if (!activeReferenceTarget) return;
  referenceSearchState.page = Math.max(1, referenceSearchState.page + pageChange);
  const params = new URLSearchParams();
  if (referenceSearchState.currentQuery) params.set("q", referenceSearchState.currentQuery);
  params.set("page_size", String(REFERENCE_PAGE_SIZE));
  params.set("page", String(referenceSearchState.page));
  const { items, total } = await fetchJSON(`/api/images?${params.toString()}`);
  referenceSearchState.totalPages = Math.max(1, Math.ceil(total / REFERENCE_PAGE_SIZE));
  renderReferenceResults(items);
  updateReferencePagination();
}

function renderReferenceResults(items) {
  const resultsEl = document.getElementById("referenceResults");
  resultsEl.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.textContent = "No media found.";
    resultsEl.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "reference-result";
    const thumb = document.createElement("img");
    thumb.src = `/images/${item.thumbnail_file || item.file_name}`;
    thumb.alt = item.prompt_text;
    li.appendChild(thumb);
    const meta = document.createElement("div");
    meta.className = "reference-result__meta";
    const name = document.createElement("span");
    name.textContent = item.file_name;
    meta.appendChild(name);
    const date = document.createElement("span");
    date.textContent = formatDisplayDate(item.captured_at);
    meta.appendChild(date);
    li.appendChild(meta);
    li.addEventListener("click", () => {
      const picker = referencePickers[activeReferenceTarget];
      picker?.addReference(item);
      closeModal("referenceModal");
    });
    li.style.cursor = "pointer";
    resultsEl.appendChild(li);
  });
}

function initializeForms() {
  const uploadForm = document.getElementById("uploadForm");
  forms.upload = {
    form: uploadForm,
    promptInput: uploadForm.querySelector('textarea[name="prompt_text"]'),
    promptMetaInput: uploadForm.querySelector('input[name="prompt_meta"]'),
    mediaTypeSelect: document.getElementById("uploadMediaType"),
    thumbnailInput: uploadForm.querySelector('input[name="thumbnail_file"]'),
    thumbnailField: document.querySelector('[data-thumbnail-field="upload"]'),
    thumbnailDirty: false,
  };

  const editForm = document.getElementById("editForm");
  forms.edit = {
    form: editForm,
    promptInput: document.getElementById("editPrompt"),
    promptMetaInput: document.getElementById("editPromptMeta"),
    mediaTypeSelect: document.getElementById("editMediaType"),
    thumbnailInput: document.querySelector('[data-thumbnail-field="edit"] input[name="thumbnail_file"]'),
    thumbnailField: document.querySelector('[data-thumbnail-field="edit"]'),
    thumbnailDirty: false,
  };
}

function initializeReferencePickers() {
  referencePickers.upload = new ReferencePicker({
    listElement: document.querySelector('[data-reference-list="upload"]'),
    onChange: () => handleReferenceUpdate("upload"),
  });
  referencePickers.edit = new ReferencePicker({
    listElement: document.querySelector('[data-reference-list="edit"]'),
    onChange: () => handleReferenceUpdate("edit"),
  });
}

function updateThumbnailVisibility() {
  const uploadState = forms.upload;
  if (!uploadState?.thumbnailField) return;
  const isVideo = uploadState.mediaTypeSelect.value === "video";
  uploadState.thumbnailField.hidden = !isVideo;
  if (!isVideo && uploadState.thumbnailInput) {
    uploadState.thumbnailInput.value = "";
    uploadState.thumbnailDirty = false;
  }
}

function applyThumbnailStyle() {
  const gallery = document.getElementById("gallery");
  if (gallery) {
    gallery.dataset.thumbStyle = state.thumbnailStyle;
  }
  const select = document.getElementById("thumbnailStyle");
  if (select) {
    select.value = state.thumbnailStyle;
  }
  localStorage.setItem(THUMBNAIL_STYLE_KEY, state.thumbnailStyle);
}

function renderCards(items) {
  state.items = items;
  const gallery = document.getElementById("gallery");
  gallery.dataset.thumbStyle = state.thumbnailStyle;
  gallery.innerHTML = "";
  const template = document.getElementById("image-card-template");

  items.forEach((item) => {
    const fragment = template.content.cloneNode(true);
    const imageEl = fragment.querySelector("[data-image]");
    const thumb = item.thumbnail_file || item.file_name;
    imageEl.src = `/images/${thumb}`;
    imageEl.alt = item.prompt_text;
    imageEl.addEventListener("click", () => openDetailModal(item.id));
    const badge = fragment.querySelector("[data-video-badge]");
    badge.hidden = item.media_type !== "video";

    const ratingEl = fragment.querySelector("[data-rating]");
    renderStars(ratingEl, item.rating);
  const dateEl = fragment.querySelector("[data-date]");
  dateEl.textContent = formatDisplayDate(item.captured_at);

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
  const mediaType = document.getElementById("mediaTypeFilter").value;

  if (query) params.set("q", query);
  if (tags.length) params.set("tags", tags.join(","));
  if (ratingMin) params.set("rating_min", ratingMin);
  if (ratingMax) params.set("rating_max", ratingMax);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (mediaType) params.set("media_type", mediaType);

  params.set("page", String(state.page));
  params.set("page_size", String(state.pageSize));

  const { items, total } = await fetchJSON(`/api/images?${params.toString()}`);
  state.total = total;
  renderCards(items);
  renderPagination();
  updateResultsSummary();
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
  syncPromptMeta("upload");
  const formData = new FormData(form);
  const tags = serializeTagsInput(formData.get("tags") || "");
  formData.set("tags", JSON.stringify(tags));
  formData.set("prompt_meta", forms.upload.promptMetaInput.value || "");

  try {
    const response = await fetch("/api/images", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("Upload failed");
    }
    form.reset();
    referencePickers.upload.setReferences([]);
    forms.upload.mediaTypeSelect.value = "image";
    updateThumbnailVisibility();
    syncPromptMeta("upload");
    closeModal("uploadModal");
    await populateTags();
    await refreshGallery(true);
    updateTagSummary();
    capturedAtDirty = false;
    forms.upload.thumbnailDirty = false;
  } catch (error) {
    alert(error.message);
  }
}

async function openEditModal(imageId) {
  const detail = await fetchImageDetail(imageId);
  if (!detail) return;
  document.getElementById("editImageId").value = detail.id;
  document.getElementById("editPrompt").value = detail.prompt_text;
  document.getElementById("editTags").value = detail.tags.map((tag) => tag.name).join(", ");
  document.getElementById("editModel").value = detail.ai_model || "";
  document.getElementById("editNotes").value = detail.notes || "";
  document.getElementById("editRating").value = detail.rating ?? "";
  document.getElementById("editMediaType").value = detail.media_type || "image";
  const references = await resolveReferences(detail.prompt_meta);
  referencePickers.edit.setReferences(references);
  syncPromptMeta("edit");
  openModal("editModal");
}

async function handleEdit(event) {
  event.preventDefault();
  const id = document.getElementById("editImageId").value;
  const promptText = document.getElementById("editPrompt").value;
  const references = referencePickers.edit.getReferences();
  const promptMeta = buildPromptMeta(promptText, references);
  const payload = {
    prompt_text: promptText,
    tags: serializeTagsInput(document.getElementById("editTags").value),
    ai_model: document.getElementById("editModel").value || null,
    notes: document.getElementById("editNotes").value || null,
    rating: document.getElementById("editRating").value ? Number(document.getElementById("editRating").value) : null,
    media_type: document.getElementById("editMediaType").value,
    prompt_meta: promptMeta,
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
    state.detailCache.delete(id);
    await populateTags();
    await refreshGallery();
    updateTagSummary();
  } catch (error) {
    alert(error.message);
  }
}

async function openDetailModal(imageId) {
  const detail = await fetchImageDetail(imageId);
  if (!detail) return;
  renderDetailMedia(detail);
  const promptEl = document.getElementById("detailPrompt");
  const promptText = detail.prompt_text || "None";
  promptEl.textContent = promptText;
  document.getElementById("detailCapturedAt").textContent = detail.captured_at
    ? new Date(detail.captured_at).toUTCString()
    : "Unknown";
  document.getElementById("detailModel").textContent = detail.ai_model || "Unknown";
  document.getElementById("detailRating").textContent =
    typeof detail.rating === "number" ? `${detail.rating}/5` : "Unrated";
  document.getElementById("detailNotes").textContent = detail.notes || "None";
  const tagContainer = document.getElementById("detailTags");
  renderTags(tagContainer, detail.tags);
  const references = await resolveReferences(detail.prompt_meta);
  renderDetailReferences(references);
  openModal("detailModal");
}

function wireEvents() {
  document.getElementById("clearFiltersButton").addEventListener("click", clearFilters);
  document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      refreshGallery(true);
    }
  });
  document.getElementById("addImageButton").addEventListener("click", () => {
    referencePickers.upload.setReferences([]);
    forms.upload.thumbnailDirty = false;
    updateThumbnailVisibility();
    openModal("uploadModal");
  });
  document.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", (event) => closeModal(event.currentTarget.dataset.closeModal));
  });
  document.getElementById("uploadModal").addEventListener("close", () => {
    capturedAtDirty = false;
  });
  forms.upload.form.addEventListener("submit", handleUpload);
  forms.edit.form.addEventListener("submit", handleEdit);
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
  const tagFilterDetails = document.querySelector(".tag-filter");
  if (tagFilterDetails) {
    tagFilterDetails.addEventListener("toggle", (event) => {
      if (!event.target.open) {
        refreshGallery(true);
      }
    });
  }
  document.getElementById("mediaTypeFilter").addEventListener("change", () => refreshGallery(true));
  const fileInput = document.querySelector('input[name="media_file"]');
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

  forms.upload.mediaTypeSelect.addEventListener("change", () => {
    updateThumbnailVisibility();
    maybeAutoFillThumbnail("upload");
  });
  if (forms.upload.thumbnailInput) {
    forms.upload.thumbnailInput.addEventListener("change", () => {
      forms.upload.thumbnailDirty = (forms.upload.thumbnailInput.files?.length || 0) > 0;
    });
  }
  if (forms.upload.promptInput) {
    forms.upload.promptInput.addEventListener("input", () => syncPromptMeta("upload"));
  }
  if (forms.edit.promptInput) {
    forms.edit.promptInput.addEventListener("input", () => syncPromptMeta("edit"));
  }
  document.querySelectorAll("[data-add-reference]").forEach((button) => {
    button.addEventListener("click", (event) => {
      openReferencePickerModal(event.currentTarget.dataset.addReference);
    });
  });
  document.getElementById("referenceSearchButton").addEventListener("click", performReferenceSearch);
  document.getElementById("referenceSearchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      performReferenceSearch();
    }
  });
  document.getElementById("referencePrevPage").addEventListener("click", () => fetchReferencePage(-1));
  document.getElementById("referenceNextPage").addEventListener("click", () => fetchReferencePage(1));

  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("blur", () => refreshGallery(true));
  }
  const ratingMinInput = document.getElementById("ratingMin");
  const ratingMaxInput = document.getElementById("ratingMax");
  ratingMinInput.addEventListener("blur", () => refreshGallery(true));
  ratingMaxInput.addEventListener("blur", () => refreshGallery(true));
  const dateFromInput = document.getElementById("dateFrom");
  const dateToInput = document.getElementById("dateTo");
  dateFromInput.addEventListener("change", () => refreshGallery(true));
  dateToInput.addEventListener("change", () => refreshGallery(true));
}

async function bootstrap() {
  initializeForms();
  initializeReferencePickers();
  updateThumbnailVisibility();
  applyThumbnailStyle();
  const styleSelect = document.getElementById("thumbnailStyle");
  if (styleSelect) {
    styleSelect.addEventListener("change", (event) => {
      state.thumbnailStyle = event.target.value;
      applyThumbnailStyle();
    });
  }
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
  document.getElementById("mediaTypeFilter").value = "";
  const tagSelect = document.getElementById("tagFilter");
  Array.from(tagSelect.options).forEach((option) => {
    option.selected = false;
  });
  updateTagSummary();
  state.thumbnailStyle = DEFAULT_THUMBNAIL_STYLE;
  applyThumbnailStyle();
  refreshGallery(true);
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

function updateResultsSummary() {
  const summary = document.getElementById("resultsSummary");
  if (!summary) return;
  const noun = state.total === 1 ? "item" : "items";
  summary.textContent = `Showing ${state.total} ${noun}`;
}
function renderDetailMedia(detail) {
  const imageEl = document.getElementById("detailImage");
  const videoEl = document.getElementById("detailVideo");
  if (detail.media_type === "video") {
    videoEl.hidden = false;
    videoEl.src = `/images/${detail.file_name}`;
    videoEl.poster = detail.thumbnail_file ? `/images/${detail.thumbnail_file}` : "";
    imageEl.hidden = true;
  } else {
    imageEl.hidden = false;
    imageEl.src = `/images/${detail.file_name}`;
    imageEl.alt = detail.prompt_text;
    videoEl.hidden = true;
    videoEl.pause();
  }
}

function renderDetailReferences(references) {
  const container = document.getElementById("detailReferences");
  container.innerHTML = "";
  if (!references.length) {
    container.textContent = "None";
    return;
  }
  references.forEach((ref) => {
    const card = document.createElement("div");
    card.className = "detail-reference";
    card.addEventListener("click", () => openDetailModal(ref.id));
    const img = document.createElement("img");
    img.src = ref.thumbnail_file ? `/images/${ref.thumbnail_file}` : `/images/${ref.file_name}`;
    img.alt = ref.prompt_text || "Reference";
    card.appendChild(img);
    const label = document.createElement("span");
    label.textContent = ref.media_type === "video" ? "Video" : "Image";
    card.appendChild(label);
    container.appendChild(card);
  });
}

async function fetchImageDetail(id) {
  if (!id) return null;
  if (state.detailCache.has(id)) {
    return state.detailCache.get(id);
  }
  const detail = await fetchJSON(`/api/images/${id}`);
  state.detailCache.set(id, detail);
  return detail;
}

async function resolveReferences(promptMeta) {
  if (!Array.isArray(promptMeta)) {
    return [];
  }
  const referenceEntries = promptMeta.slice(0, -1);
  const resolved = [];
  for (const entry of referenceEntries) {
    if (!entry?.id) continue;
    const detail = await fetchImageDetail(entry.id);
    if (!detail) continue;
    resolved.push({
      id: detail.id,
      prompt_text: detail.prompt_text,
      thumbnail_file: detail.thumbnail_file,
      file_name: detail.file_name,
      media_type: detail.media_type,
      captured_at: detail.captured_at,
    });
  }
  return resolved;
}
function updateReferencePagination() {
  const prev = document.getElementById("referencePrevPage");
  const next = document.getElementById("referenceNextPage");
  const indicator = document.getElementById("referencePageIndicator");
  if (!prev || !next || !indicator) return;
  prev.disabled = referenceSearchState.page <= 1;
  next.disabled = referenceSearchState.page >= referenceSearchState.totalPages;
  indicator.textContent = `Page ${referenceSearchState.page} of ${referenceSearchState.totalPages}`;
}
