/** Use identical date text during static rendering and browser hydration. */
export function formatDate(value) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value)) + " UTC";
}
