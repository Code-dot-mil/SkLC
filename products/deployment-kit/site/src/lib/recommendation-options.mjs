export const RECOMMENDATION_OPTIONS = [
  { value: "all", label: "All recommendations" },
  { value: "DO_NOT_INSTALL", label: "Avoid installing" },
  { value: "CAUTION", label: "Use caution" },
  { value: "SAFE", label: "Safe to use" },
  { value: "Unknown", label: "Unknown" },
];

export const RECOMMENDATION_VALUES = RECOMMENDATION_OPTIONS.map(({ value }) => value);
