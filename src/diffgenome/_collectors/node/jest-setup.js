"use strict";
/*
 * Jest integration: marks each test as a stimulus and writes its Execution when it ends.
 * Loaded through the workspace Jest config (setupFilesAfterEnv, or setupTestFrameworkScriptFile
 * on Jest < 24) with DIFFGENOME_RUNTIME pointing at runtime.js. Works with the jasmine2
 * runner (reporter API) and with jest-circus (beforeEach/afterEach + expect state).
 */
const runtime = require(process.env.DIFFGENOME_RUNTIME);
if (process.env.DIFFGENOME_CHAIN_SETUP) require(process.env.DIFFGENOME_CHAIN_SETUP);

function refFor(fullName) {
  const state = typeof expect !== "undefined" && expect.getState ? expect.getState() : {};
  const file = state.testPath ? require("path").relative(process.cwd(), state.testPath) : "";
  return file ? `${file}::${fullName}` : fullName;
}

if (typeof jasmine !== "undefined" && jasmine.getEnv) {
  jasmine.getEnv().addReporter({
    specStarted(result) {
      runtime.begin(refFor(result.fullName));
    },
    specDone(result) {
      runtime.end(result.status === "passed" ? "passed" : result.status === "pending" ? "skipped" : "failed");
    },
  });
} else {
  let failedBefore = 0;
  beforeEach(() => {
    const s = expect.getState();
    failedBefore = s.assertionCalls;
    runtime.begin(refFor(s.currentTestName || "unknown"));
  });
  afterEach(() => {
    const s = expect.getState();
    // jest-circus does not expose the status in afterEach; a failed expectation leaves
    // suppressedErrors, an uncaught throw skips afterEach entirely.
    const failed = s.suppressedErrors && s.suppressedErrors.length > 0;
    runtime.end(failed ? "failed" : "passed");
  });
}
