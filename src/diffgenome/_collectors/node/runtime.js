"use strict";
/*
 * diffgenome Node runtime: receives events from source-instrumented code and emits one
 * Execution (diffgenome event protocol, JSON) per stimulus. No dependencies.
 *
 * Attribution uses AsyncLocalStorage: `run` (async functions, generators) scopes the
 * store to the body so continuations after `await` keep their parent and the caller's
 * store is restored on the synchronous return; `enter`/`exit` (sync functions) set and
 * restore the store explicitly. Observer integrity: everything this module needs is bound
 * at load time (fs, crypto, path, the AsyncLocalStorage class), so a target that patches
 * globals or modules later cannot redirect it.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { AsyncLocalStorage } = require("async_hooks");
const net = require("net");

const createHash = crypto.createHash;
const writeFileSync = fs.writeFileSync;
const mkdirSync = fs.mkdirSync;
const joinPath = path.join;
const ObjectKeys = Object.keys;
const ObjectGetPrototypeOf = Object.getPrototypeOf;
const ArrayIsArray = Array.isArray;
const JSONStringify = JSON.stringify;

const als = new AsyncLocalStorage();
const MAX_ARGS = 8;
const DIGEST_DEPTH = 3;
const DIGEST_WIDTH = 16;

const state = {
  active: false,
  stimulus: process.env.DIFFGENOME_STIMULUS || "existing_test",
  outDir: process.env.DIFFGENOME_OUT || null,
  revision: process.env.DIFFGENOME_REVISION || null,
  ref: null,
  nodes: [],
  symbols: new Map(),
  diagnostics: [],
  egress: 0,
};

// ----------------------------------------------------------------------------- summaries

function shape(v) {
  if (v === null) return "null";
  const t = typeof v;
  if (t === "undefined" || t === "boolean" || t === "number" || t === "bigint" || t === "string" || t === "symbol") return t;
  if (t === "function") return v._isMockFunction ? "stand-in" : "function";
  if (ArrayIsArray(v)) return `array[${v.length}]`;
  if (v instanceof Promise) return "Promise";
  const proto = ObjectGetPrototypeOf(v);
  if (proto === null || proto === Object.prototype) return `object[${ObjectKeys(v).length}]`;
  const name = proto.constructor && proto.constructor.name;
  return name || "object";
}

function canonical(v, depth) {
  if (v === null) return "null";
  const t = typeof v;
  if (t === "undefined") return "undefined";
  if (t === "boolean" || t === "number" || t === "bigint") return `${t}:${String(v)}`;
  if (t === "string") return `string:${JSONStringify(v)}`;
  if (t === "symbol" || t === "function") return null;
  if (depth === 0) return null;
  if (ArrayIsArray(v)) {
    if (v.length > DIGEST_WIDTH) return null;
    const parts = [];
    for (const x of v) {
      const c = canonical(x, depth - 1);
      if (c === null) return null;
      parts.push(c);
    }
    return `array[${parts.join(",")}]`;
  }
  if (v instanceof Promise || v instanceof Date || v instanceof RegExp || v instanceof Map || v instanceof Set) return null;
  const proto = ObjectGetPrototypeOf(v);
  const plain = proto === null || proto === Object.prototype;
  const keys = ObjectKeys(v);
  if (keys.length > DIGEST_WIDTH) return null;
  const items = [];
  for (const k of keys.sort()) {
    const c = canonical(v[k], depth - 1);
    if (c === null) return null;
    items.push(`${k}=${c}`);
  }
  const name = plain ? "object" : (proto.constructor && proto.constructor.name) || "object";
  return `${name}{${items.join(",")}}`;
}

function digest(v) {
  const c = canonical(v, DIGEST_DEPTH);
  if (c === null) return "";
  return createHash("sha256").update(c).digest("hex").slice(0, 16);
}

function argShapes(names, values) {
  const out = [];
  const n = Math.min(values.length, MAX_ARGS);
  for (let i = 0; i < n; i++) {
    const name = names && names[i] ? names[i] : `arg${i}`;
    out.push([name, shape(values[i]), digest(values[i])]);
  }
  return out;
}

// ----------------------------------------------------------------------------- state facts

const STATE_WIDTH = 16;

function bucket(v) {
  if (v === null || v === undefined) return ["none", ""];
  const t = typeof v;
  if (t === "boolean") return [`bool:${v}`, ""];
  if (t === "number" || t === "bigint") return [v == 0 ? "num:zero" : v > 0 ? "num:pos" : "num:neg", ""];
  if (t === "string") return [v.length ? "str:nonempty" : "str:empty", ""];
  if (t === "function") return v._isMockFunction ? ["obj:stand-in", ""] : null;
  if (ArrayIsArray(v)) return [v.length === 0 ? "coll:empty" : v.length === 1 ? "coll:one" : "coll:many", ""];
  if (v instanceof Map || v instanceof Set) return [v.size === 0 ? "coll:empty" : v.size === 1 ? "coll:one" : "coll:many", ""];
  if (v && typeof v === "object" && v._isMockObject) return ["obj:stand-in", ""];
  const proto = ObjectGetPrototypeOf(v);
  if (proto === null || proto === Object.prototype) return [`coll:${ObjectKeys(v).length === 0 ? "empty" : ObjectKeys(v).length === 1 ? "one" : "many"}`, ""];
  const name = (proto.constructor && proto.constructor.name) || "object";
  return [`obj:${name}`, digest(name)];
}

function stateFacts(receiver) {
  if (receiver === undefined || receiver === null || typeof receiver !== "object") return [];
  const facts = [];
  const proto = ObjectGetPrototypeOf(receiver);
  const name = (proto && proto.constructor && proto.constructor.name) || "object";
  facts.push(["self:type", `obj:${name}`, digest(name)]);
  for (const k of ObjectKeys(receiver).slice(0, STATE_WIDTH)) {
    const b = bucket(receiver[k]);
    if (b) facts.push([`self.${k}`, b[0], b[1]]);
  }
  return facts;
}

// ----------------------------------------------------------------------------- nodes

function currentNode() {
  const store = als.getStore();
  return store ? store.node : null;
}

function intern(symbol, origin, file, line) {
  if (!state.symbols.has(symbol)) {
    state.symbols.set(symbol, { id: symbol, origin, location: file ? { path: file, line } : null });
  }
}

function nodeOrigin(id) {
  const n = state.nodes[id];
  if (!n || n.type !== "call") return "unknown";
  const s = state.symbols.get(n.symbol);
  return s ? s.origin : "unknown";
}

function newCall(symbol, args, parent, facts) {
  const id = state.nodes.length;
  state.nodes.push({
    type: "call", id, parent, symbol, collector: 0, args, thread: 0, outcome: "unknown", result: "",
    state: facts || [],
  });
  return id;
}

function newSubstitution(parent, mechanism, substitute, claimed, relation, pathParts, args, facts) {
  const id = state.nodes.length;
  state.nodes.push({
    type: "substitution", id, parent, collector: 0, mechanism, substitute, claimed_target: claimed,
    relation, path: pathParts, args, outcome: "unknown", result: "", state: facts || [],
  });
  return id;
}

function settle(id, outcome, result) {
  const n = state.nodes[id];
  if (!n || n.outcome !== "unknown") return;
  n.outcome = outcome;
  n.result = result || "";
}

function errorSymbol(e) {
  const name = e && e.constructor && e.constructor.name ? e.constructor.name : "Error";
  const sym = `js:${name}`;
  intern(sym, "external", null, 0);
  return sym;
}

const classSymbols = new Map(); // constructor -> {sym, origin}

/** Registered by instrumented modules after each named top-level class declaration. */
function registerClass(ctor, sym, origin) {
  if (typeof ctor === "function") classSymbols.set(ctor, { sym, origin });
}

/** A test-origin method overriding a repo class's member: the fake's claim is that member,
 * found by walking `this`'s prototype chain to the nearest registered repo class that
 * defines the same name. Identity through the prototype chain, not a name match. */
function overriddenMember(meta, thisArg) {
  if (thisArg === undefined || thisArg === null) return null;
  const member = meta.sym.slice(meta.sym.lastIndexOf(".") + 1);
  if (!member || member.startsWith("<")) return null;
  let proto = ObjectGetPrototypeOf(thisArg);
  let hops = 0;
  while (proto && proto !== Object.prototype && hops < 20) {
    const reg = classSymbols.get(proto.constructor);
    if (reg && reg.origin === "repo" && Object.prototype.hasOwnProperty.call(proto, member)) {
      const sym = `${reg.sym}.${member}`;
      intern(sym, "repo", null, 0);
      return sym;
    }
    proto = ObjectGetPrototypeOf(proto);
    hops += 1;
  }
  return null;
}

/** Called on function entry. `meta`: {sym, origin, file, line, params}. Returns a context. */
function enter(meta, values, thisArg) {
  if (!state.active) return null;
  intern(meta.sym, meta.origin, meta.file, meta.line);
  const args = argShapes(meta.params, values);
  let parent = currentNode();
  if (parent === null) parent = 0; // the stimulus root created by begin()
  let sub = null;
  if (meta.origin === "test" && nodeOrigin(parent) === "repo") {
    // Production code called into test-defined code: a fake/stub that executes.
    const mechanism = meta.sym.includes(".") && !/\.<anon>@\d+$/.test(meta.sym) ? "fake" : "stub";
    let claimed = null;
    let relation = "none";
    const overridden = overriddenMember(meta, thisArg);
    if (overridden) { claimed = overridden; relation = "overrides"; }
    // A subclass fake's inherited fields are the real receiver's state.
    sub = newSubstitution(parent, mechanism, meta.sym, claimed, relation, [], args, claimed ? stateFacts(thisArg) : []);
    parent = sub;
  }
  const id = newCall(meta.sym, args, parent, stateFacts(thisArg));
  const prev = als.getStore();
  als.enterWith({ node: id });
  return { id, prev, sub };
}

function exit(ctx) {
  if (!ctx) return;
  settle(ctx.id, "returned", "");
  if (ctx.sub !== null) settle(ctx.sub, state.nodes[ctx.id].outcome, state.nodes[ctx.id].result);
  als.enterWith(ctx.prev || { node: null });
}

function ret(ctx, value) {
  if (!ctx) return value;
  if (value && typeof value.then === "function") {
    value.then(
      (v) => { settle(ctx.id, "returned", digest(v)); if (ctx.sub !== null) settle(ctx.sub, "returned", digest(v)); },
      (e) => { const s = "raised:" + errorSymbol(e); settle(ctx.id, s, ""); if (ctx.sub !== null) settle(ctx.sub, s, ""); },
    );
    return value;
  }
  settle(ctx.id, "returned", digest(value));
  if (ctx.sub !== null) settle(ctx.sub, "returned", digest(value));
  return value;
}

function throwed(ctx, e) {
  if (!ctx) return;
  const s = "raised:" + errorSymbol(e);
  settle(ctx.id, s, "");
  if (ctx.sub !== null) settle(ctx.sub, s, "");
}

/** Async functions and generators: scope the store to the body via als.run. */
function run(meta, values, thisArg, fn) {
  if (!state.active) return fn.call(thisArg, null);
  const ctx = enter(meta, values, thisArg);
  // enter() used enterWith; undo that and use run() so the caller's store is restored on
  // the synchronous return and continuations inside keep the body's store.
  als.enterWith(ctx.prev || { node: null });
  let result;
  try {
    result = als.run({ node: ctx.id }, () => fn.call(thisArg, ctx));
  } catch (e) {
    throwed(ctx, e);
    throw e;
  }
  return ret(ctx, result);
}

// ----------------------------------------------------------------------------- call sites

function describeMock(f) {
  const name = typeof f.getMockName === "function" ? f.getMockName() : "";
  const pathParts = name && name !== "jest.fn()" && name !== "mockConstructor" ? [name] : [];
  return { substitute: "js:jest.fn", claimed: null, relation: "none", pathParts };
}

function recordStandIn(f, values) {
  if (!state.active) return;
  const parent = currentNode();
  const d = describeMock(f);
  const id = newSubstitution(parent === null ? 0 : parent, "mock_object", d.substitute, d.claimed, d.relation, d.pathParts, argShapes(null, values));
  return id;
}

function finishStandIn(id, value) {
  if (id === undefined) return value;
  if (value && typeof value.then === "function") {
    value.then((v) => settle(id, "returned", digest(v)), (e) => settle(id, "raised:" + errorSymbol(e), ""));
    return value;
  }
  settle(id, "returned", digest(value));
  return value;
}

/** obj.key(...args) */
function callm(obj, key, args) {
  const f = obj == null ? undefined : obj[key];
  if (typeof f !== "function") {
    throw new TypeError(`${obj == null ? "undefined" : shape(obj)}.${String(key)} is not a function`);
  }
  if (f._isMockFunction) {
    const id = recordStandIn(f, args);
    try {
      return finishStandIn(id, f.apply(obj, args));
    } catch (e) {
      if (id !== undefined) settle(id, "raised:" + errorSymbol(e), "");
      throw e;
    }
  }
  return f.apply(obj, args);
}

/** f(...args) */
function callf(f, args) {
  if (typeof f !== "function") throw new TypeError(`${String(f)} is not a function`);
  if (f._isMockFunction) {
    const id = recordStandIn(f, args);
    try {
      return finishStandIn(id, f.apply(undefined, args));
    } catch (e) {
      if (id !== undefined) settle(id, "raised:" + errorSymbol(e), "");
      throw e;
    }
  }
  return f.apply(undefined, args);
}

// Call sites are instrumented at the callee, never around the call's value, so TypeScript
// sees the original call: its signature, overloads, type predicates and contextual types.
// Only a Jest mock is ever substituted -- by a wrapper that records the stand-in and calls
// it exactly as the original call would have.

function recordingStandIn(fn, receiver) {
  return function (...args) {
    const id = recordStandIn(fn, args);
    try {
      return finishStandIn(id, fn.apply(receiver, args));
    } catch (e) {
      if (id !== undefined) settle(id, "raised:" + errorSymbol(e), "");
      throw e;
    }
  };
}

/** `f(args)` -> `__dg.f(f)(args)`: the function itself, or a recording stand-in for a mock. */
function f(fn) {
  return typeof fn === "function" && fn._isMockFunction ? recordingStandIn(fn, undefined) : fn;
}

/** `obj.key(args)` -> `__dg.m(obj, "key").key(args)`. The member is read once, here, and the
 * call goes to it with `obj` as the receiver, exactly as the original call would. */
function m(obj, key) {
  const fn = obj[key]; // a null/undefined `obj` throws here, as the original member read would
  // not callable: the call itself throws once its arguments are evaluated, as it would have
  if (typeof fn !== "function") return { [key]: fn };
  if (fn._isMockFunction) return { [key]: recordingStandIn(fn, obj) };
  return { [key]: function (...args) { return fn.apply(obj, args); } };
}

// A statement `assertFoo(x);` / `this.check(x);` is left exactly as written -- an assertion
// function only narrows when called through a plain or dotted name -- and observed from
// either side: `const t = __dg.pre(callee); <statement>; __dg.post(t);`. A mock's own
// record (`mock.calls`/`mock.results`) supplies the arguments and outcome, including a
// throw that skips `post`, which end() settles.
let pending = [];

function pre(fn) {
  if (!state.active || typeof fn !== "function" || !fn._isMockFunction || !fn.mock) return null;
  const parent = currentNode();
  const d = describeMock(fn);
  const id = newSubstitution(parent === null ? 0 : parent, "mock_object", d.substitute, d.claimed, d.relation, d.pathParts, []);
  const token = { id, fn, index: fn.mock.calls.length, done: false };
  pending.push(token);
  return token;
}

function post(token) {
  if (!token || token.done) return;
  token.done = true;
  const node = state.nodes[token.id];
  const call = token.fn.mock.calls[token.index];
  const result = token.fn.mock.results[token.index];
  if (!node || !call) return;
  node.args = argShapes(null, call);
  if (!result || result.type === "incomplete") return;
  if (result.type === "throw") settle(token.id, "raised:" + errorSymbol(result.value), "");
  else finishStandIn(token.id, result.value);
}

// ----------------------------------------------------------------------------- egress guard

function isLoopback(host) {
  return host === undefined || host === null || host === "" || host === "localhost" || host === "127.0.0.1" || host === "::1" || host === "0.0.0.0" || host === "::";
}

function installEgressGuard() {
  const original = net.Socket.prototype.connect;
  net.Socket.prototype.connect = function (...args) {
    let host = "";
    let port = "";
    const a = args[0];
    if (a && typeof a === "object" && !ArrayIsArray(a)) { host = a.host || a.path || ""; port = a.port || ""; }
    else if (typeof a === "number") { port = a; host = typeof args[1] === "string" ? args[1] : ""; }
    else if (typeof a === "string") { host = a; }
    const target = host ? `${host}:${port}` : `:${port}`;
    const allowed = isLoopback(host);
    if (state.active) {
      const parent = currentNode();
      state.nodes.push({
        type: "os_event", id: state.nodes.length, parent: parent === null ? 0 : parent, collector: 1,
        kind: "connect", target, outcome: allowed ? "allowed:loopback" : "refused:egress-guard", native_symbol: null,
      });
    }
    if (!allowed) {
      state.egress += 1;
      throw new Error(`diffgenome egress guard: connect to ${target} refused`);
    }
    return original.apply(this, args);
  };
}

// ----------------------------------------------------------------------------- stimulus

function begin(ref) {
  pending = [];
  state.active = true;
  state.ref = ref;
  state.nodes = [];
  state.symbols = new Map();
  state.diagnostics = [];
  state.egress = 0;
  // Node 0 is the stimulus itself; every in-scope call with no in-scope caller hangs off it.
  const sym = `js:${ref}`;
  intern(sym, "test", null, 0);
  newCall(sym, [], null);
  als.enterWith({ node: null });
}

function end(outcome) {
  for (const token of pending) post(token);
  pending = [];
  state.active = false;
  if (!state.outDir || state.ref === null) return null;
  const execution = {
    id: `${state.ref}@${state.revision || "unknown"}`,
    stimulus: state.stimulus,
    stimulus_ref: state.ref,
    outcome,
    revision: state.revision,
    collectors: [
      { name: "node-source-instrumentation", plane: "symbol", fidelity: "complete" },
      { name: "node-egress-guard", plane: "os", fidelity: "complete" },
    ],
    symbols: [...state.symbols.values()].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)),
    nodes: state.nodes,
    diagnostics: [["egress_attempts", String(state.egress)]],
  };
  mkdirSync(state.outDir, { recursive: true });
  const h = createHash("sha256").update(state.ref).digest("hex").slice(0, 12);
  const name = state.ref.replace(/[^A-Za-z0-9_.-]+/g, "_").slice(0, 100);
  writeFileSync(joinPath(state.outDir, `${name}-${h}.json`), JSONStringify(execution, null, 1) + "\n");
  return execution;
}

installEgressGuard();

module.exports = { enter, exit, ret, throwed, run, callm, callf, f, m, pre, post, begin, end, registerClass, _state: state };
