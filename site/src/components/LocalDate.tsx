import { useEffect, useState } from "react";

import { formatDate } from "../lib/format-date.mjs";

export default function LocalDate({ value }: { value?: string }) {
  const [localized, setLocalized] = useState(false);
  useEffect(() => setLocalized(true), []);

  if (!value) return <span>Unknown</span>;

  // Keep the static page and first hydration render identical. After mounting,
  // use the browser's locale and timezone; without JS the labeled UTC date remains.
  const options = localized ? undefined : { locale: "en-US", timeZone: "UTC" };
  return <time dateTime={value}>{formatDate(value, options)}</time>;
}
