const gallery = document.getElementById("gallery");

async function loadGallery() {
  try {
    const response = await fetch("/api/images");
    if (!response.ok) {
      throw new Error("API request failed");
    }
    const payload = await response.json();
    gallery.innerHTML = "";
    payload.items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "card";
      card.innerHTML = `
        <img src="/images/${item.file_name}" alt="${item.prompt_text}" loading="lazy" />
        <div class="card__body">
          <h2>${item.ai_model || "Unknown Model"}</h2>
          <p>${item.prompt_text}</p>
          <div class="tags">${item.tags.map((tag) => `<span class="tag">${tag.name}</span>`).join("")}</div>
        </div>
      `;
      gallery.appendChild(card);
    });
  } catch (error) {
    gallery.innerHTML = `<p class="error">Failed to load gallery: ${error.message}</p>`;
  }
}

loadGallery();
