import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const { rank } = createRequire(import.meta.url)("../site/score.js");
const cases = JSON.parse(readFileSync(new URL("./fixtures/parity.json", import.meta.url)));

cases.forEach((c, i) => {
  test(`parity case ${i}: budget ${c.budget}, max ${c.max_commute}`, () => {
    assert.deepEqual(rank(c.rows, c.budget, c.max_commute, c.hub_name), c.expected);
  });
});
