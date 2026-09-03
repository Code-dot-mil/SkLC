export const showSourceLinks = readBooleanEnv("SKLC_SHOW_SOURCE_LINKS", {
  defaultValue: true,
});

export function readBooleanEnv(name, { defaultValue } = {}) {
  const rawValue = process.env[name];
  if (rawValue === undefined) {
    if (defaultValue === undefined) {
      throw new Error(`${name} must be set to true or false.`);
    }
    return defaultValue;
  }

  const normalized = rawValue.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }

  throw new Error(`${name} must be true or false, got ${JSON.stringify(rawValue)}.`);
}
