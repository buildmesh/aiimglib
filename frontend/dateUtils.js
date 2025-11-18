const ISO_FILENAME_REGEX =
  /(\d{4})[-_T]?(\d{2})[-_T]?(\d{2})(?:[-_T]?(\d{2})[-_T]?(\d{2})[-_T]?(\d{2}))?/;

export function parseUtcDateFromFilename(filename = "") {
  if (!filename) return null;
  const dotIndex = filename.lastIndexOf(".");
  const base = dotIndex >= 0 ? filename.slice(0, dotIndex) : filename;
  const isoMatch = /[-_T]/.test(base) ? base.match(ISO_FILENAME_REGEX) : null;
  if (isoMatch) {
    const [, year, month, day, hour = "00", minute = "00", second = "00"] = isoMatch;
    return new Date(
      Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second))
    );
  }
  const unixMatch = base.match(/(\d{10,})/);
  if (unixMatch) {
    const raw = unixMatch[1];
    const seconds = raw.length > 10 ? Number(raw) / 10 ** (raw.length - 10) : Number(raw);
    if (!Number.isNaN(seconds)) {
      return new Date(seconds * 1000);
    }
  }
  return null;
}

export function formatDateForInput(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return null;
  }
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function extractDateFromFilename(filename = "") {
  const date = parseUtcDateFromFilename(filename);
  if (!date) {
    return null;
  }
  return formatDateForInput(date);
}

const displayFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});

export function formatDisplayDate(value) {
  if (!value) return "Date unknown";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unknown";
  return displayFormatter.format(date);
}
