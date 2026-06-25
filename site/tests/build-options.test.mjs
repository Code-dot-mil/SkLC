import assert from "node:assert/strict";
import test from "node:test";

import { readBooleanEnv } from "../src/lib/build-options.mjs";

test("boolean build options use documented defaults", () => {
  delete process.env.TEST_BOOLEAN_BUILD_OPTION;

  assert.equal(readBooleanEnv("TEST_BOOLEAN_BUILD_OPTION", { defaultValue: true }), true);
  assert.equal(readBooleanEnv("TEST_BOOLEAN_BUILD_OPTION", { defaultValue: false }), false);
});

test("boolean build options accept explicit true and false values", () => {
  for (const value of ["1", "true", "yes", "on"]) {
    process.env.TEST_BOOLEAN_BUILD_OPTION = value;
    assert.equal(readBooleanEnv("TEST_BOOLEAN_BUILD_OPTION"), true);
  }

  for (const value of ["0", "false", "no", "off"]) {
    process.env.TEST_BOOLEAN_BUILD_OPTION = value;
    assert.equal(readBooleanEnv("TEST_BOOLEAN_BUILD_OPTION"), false);
  }

  delete process.env.TEST_BOOLEAN_BUILD_OPTION;
});

test("boolean build options reject invalid values", () => {
  for (const value of ["", " ", "sometimes"]) {
    process.env.TEST_BOOLEAN_BUILD_OPTION = value;
    assert.throws(
      () => readBooleanEnv("TEST_BOOLEAN_BUILD_OPTION"),
      /TEST_BOOLEAN_BUILD_OPTION must be true or false/,
    );
  }

  delete process.env.TEST_BOOLEAN_BUILD_OPTION;
});
