export function buildPromptMeta(promptText, references) {
  const cleanPrompt = typeof promptText === "string" ? promptText : "";
  const cleanedReferences = Array.isArray(references)
    ? references
        .map((ref) => (ref && ref.id ? { id: ref.id } : null))
        .filter(Boolean)
    : [];

  if (!cleanedReferences.length) {
    return cleanPrompt || null;
  }
  return [...cleanedReferences, cleanPrompt];
}

export function shouldAutoFillThumbnail(mediaType, references) {
  return (
    mediaType === "video" &&
    Array.isArray(references) &&
    references.some((ref) => Boolean(ref && (ref.thumbnail_file || ref.file_name)))
  );
}

export function getFirstReferenceAsset(references) {
  if (!Array.isArray(references) || !references.length) {
    return null;
  }
  const ref = references.find((item) => item && (item.thumbnail_file || item.file_name));
  if (!ref) {
    return null;
  }
  return {
    thumbnail: ref.thumbnail_file || null,
    file: ref.file_name || null,
  };
}
