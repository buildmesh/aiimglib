export class ReferencePicker {
  constructor({ listElement, onChange }) {
    this.listElement = listElement;
    this.onChange = onChange;
    this.references = [];
  }

  setReferences(references = []) {
    this.references = dedupeReferences(references);
    this.render();
  }

  addReference(reference) {
    this.references = dedupeReferences([...this.references, reference]);
    this.render();
  }

  removeReference(id) {
    this.references = this.references.filter((ref) => ref.id !== id);
    this.render();
  }

  getReferences() {
    return this.references.slice();
  }

  render() {
    if (!this.listElement) {
      return;
    }
    this.listElement.innerHTML = "";
    this.references.forEach((ref) => {
      const li = document.createElement("li");
      li.classList.add("reference-picker__item");
      const thumb = document.createElement("img");
      thumb.className = "reference-picker__thumb";
      thumb.src = ref.thumbnail_file ? `/images/${ref.thumbnail_file}` : `/images/${ref.file_name}`;
      thumb.alt = ref.prompt_text || "Reference";
      li.appendChild(thumb);

      const info = document.createElement("div");
      info.innerHTML = `<strong>${ref.prompt_text || "Untitled"}</strong><div class="reference-picker__meta">${
        ref.media_type || "image"
      }</div>`;
      li.appendChild(info);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "ghost";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", () => {
        this.removeReference(ref.id);
        this.onChange?.(this.getReferences());
      });
      li.appendChild(removeBtn);

      this.listElement.appendChild(li);
    });
    this.onChange?.(this.getReferences());
  }
}

function dedupeReferences(references) {
  const seen = new Set();
  const result = [];
  for (const ref of references) {
    if (!ref || !ref.id || seen.has(ref.id)) {
      continue;
    }
    seen.add(ref.id);
    result.push(ref);
  }
  return result;
}
