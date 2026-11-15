// Display helpers. The API sends money as strings ("150.00") and timestamps
// in UTC; these functions turn them into text for the screen.

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? currency.format(number) : "—";
}

// "2026-01-15" -> "Jan 15, 2026". Built from the parts so the browser's
// timezone cannot shift a calendar date to the previous day.
export function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return "—";
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// "2026-01-15T14:05:09Z" -> local date and time.
export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export function formatStatus(status) {
  if (!status) return "";
  const text = status.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
