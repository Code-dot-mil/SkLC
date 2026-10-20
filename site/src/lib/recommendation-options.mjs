export const RECOMMENDATION_OPTIONS = [
  { value: "all", label: "All recommendations" },
  { value: "CAUTION", label: "Human Review Advised" },
  { value: "SAFE", label: "Safe to use" },
  { value: "Unknown", label: "Unknown" },
];

export const RECOMMENDATION_VALUES = RECOMMENDATION_OPTIONS.map(({ value }) => value);
