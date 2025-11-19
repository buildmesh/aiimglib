import { formatDisplayDate } from "./dateUtils.js";

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
      const thumbSrc =
        ref.media_type === "video" ? ref.thumbnail_file || ref.file_name : ref.file_name;
      thumb.src = `/images/${thumbSrc}`;
      thumb.alt = ref.prompt_text || "Reference";
      li.appendChild(thumb);

      const info = document.createElement("div");
      info.className = "reference-picker__info";
      const name = document.createElement("span");
      name.textContent = ref.file_name || "Unknown file";
      info.appendChild(name);
      const date = document.createElement("span");
      date.textContent = formatDisplayDate(ref.captured_at);
      info.appendChild(date);
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
