import "./styles.css";

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
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

function renderCards(items) {
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = "";
  const template = document.getElementById("image-card-template");

  items.forEach((item) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector("[data-image]").src = `/images/${item.file_name}`;
    fragment.querySelector("[data-title]").textContent = item.ai_model || "Unknown Model";
    fragment.querySelector("[data-prompt]").textContent = item.prompt_text;
    renderTags(fragment.querySelector("[data-tags]"), item.tags);
    gallery.appendChild(fragment);
  });
}

async function refreshGallery() {
  const query = document.getElementById("searchInput").value.trim();
  const tagSelect = document.getElementById("tagFilter");
  const selectedTags = Array.from(tagSelect.selectedOptions).map((option) => option.value);

  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (selectedTags.length) params.set("tags", selectedTags.join(","));

  const { items } = await fetchJSON(`/api/images?${params.toString()}`);
  renderCards(items);
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
}

function wireEvents() {
  document.getElementById("refreshButton").addEventListener("click", refreshGallery);
  document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      refreshGallery();
    }
  });
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
