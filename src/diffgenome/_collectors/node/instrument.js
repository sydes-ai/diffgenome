#!/usr/bin/env node
"use strict";
/*
 * diffgenome Node source instrumenter.
 *
 *   node instrument.js --root <repo copy> --src <dir> [--src ...] --tests <dir> [--tests ...]
 *                      --runtime <abs path to runtime.js> --index <out.json> [--dry]
 *
 * Rewrites every .ts/.js/.tsx/.jsx file under the roots IN PLACE (the copy is disposable)
 * so that each function reports entry, return/throw and call sites to the runtime, and
 * writes a symbol index (definitions with line spans) that the Python side uses to map
 * diff lines to symbols and to extract source for probe context. Symbol naming:
 *   js:<path relative to root, no extension>.<qualified name>
 * where anonymous functions are named <anon>@<line>, the same rule the Python collector
 * uses for lambdas.
 *
 * Sync functions get try/catch/finally around the body (keeps `this`/`arguments`);
 * async functions and generators get their body moved into a callback run under the
 * runtime's AsyncLocalStorage scope, which is what makes attribution across `await`
 * correct.
 */
const fs = require("fs");
const path = require("path");
const ts = require("typescript");

function parseArgs(argv) {
  const out = { src: [], tests: [], dry: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--root") out.root = argv[++i];
    else if (a === "--src") out.src.push(argv[++i]);
    else if (a === "--tests") out.tests.push(argv[++i]);
    else if (a === "--runtime") out.runtime = argv[++i];
    else if (a === "--index") out.index = argv[++i];
    else if (a === "--dry") out.dry = true;
  }
  if (!out.root || !out.runtime) throw new Error("--root and --runtime are required");
  return out;
}

const EXCLUDED = new Set(["node_modules", "dist", "build", "coverage", "__pycache__"]);
const EXTS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || EXCLUDED.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.isFile() && EXTS.has(path.extname(entry.name)) && !entry.name.endsWith(".d.ts")) yield full;
  }
}

function moduleName(root, file) {
  const rel = path.relative(root, file).split(path.sep).join("/");
  return rel.replace(/\.(tsx?|jsx?|mjs|cjs)$/, "");
}

// ----------------------------------------------------------------------------- naming

function isFunctionLike(node) {
  return (
    ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node) || ts.isArrowFunction(node) ||
    ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ||
    ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)
  );
}

function nameOf(node, sf) {
  const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
  if (ts.isConstructorDeclaration(node)) return "constructor";
  if ((ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isFunctionExpression(node) ||
       ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) && node.name) {
    return node.name.getText(sf);
  }
  const p = node.parent;
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && ts.isPropertyAssignment(p) && p.name) return p.name.getText(sf);
  if (p && ts.isPropertyDeclaration(p) && p.name) return p.name.getText(sf);
  return `<anon>@${line}`;
}

function qualname(node, sf) {
  const parts = [];
  let cur = node;
  while (cur && !ts.isSourceFile(cur)) {
    if (isFunctionLike(cur)) parts.unshift(nameOf(cur, sf));
    else if (ts.isClassDeclaration(cur) || ts.isClassExpression(cur)) parts.unshift(cur.name ? cur.name.text : `<class>@${sf.getLineAndCharacterOfPosition(cur.getStart(sf)).line + 1}`);
    cur = cur.parent;
  }
  return parts.join(".");
}

function paramNames(node) {
  return node.parameters.map((p) => (ts.isIdentifier(p.name) ? p.name.text : "<pattern>"));
}

function paramIdentifiers(node) {
  return node.parameters.filter((p) => ts.isIdentifier(p.name)).map((p) => p.name.text);
}

// ----------------------------------------------------------------------------- transform

function instrumentFile(file, ctxInfo, index) {
  const text = fs.readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : undefined);
  const mod = moduleName(ctxInfo.root, file);
  const rel = path.relative(ctxInfo.root, file).split(path.sep).join("/");
  const f = ts.factory;
  const DG = f.createIdentifier("__dg");
  let changed = false;

  // Index definitions (functions and classes) from the original tree.
  function indexNode(node) {
    if (isFunctionLike(node) && node.body) {
      const start = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
      const end = sf.getLineAndCharacterOfPosition(node.getEnd()).line + 1;
      index.push({ symbol: `js:${mod}.${qualname(node, sf)}`, path: rel, start, end, kind: "function", is_async: !!(node.modifiers && node.modifiers.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword)) });
    } else if (ts.isClassDeclaration(node) && node.name) {
      const start = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
      const end = sf.getLineAndCharacterOfPosition(node.getEnd()).line + 1;
      index.push({ symbol: `js:${mod}.${qualname(node, sf)}`, path: rel, start, end, kind: "class", is_async: false });
    }
    ts.forEachChild(node, indexNode);
  }
  indexNode(sf);

  const transformer = (context) => {
    const ctxStack = []; // the __dgc identifier for the innermost instrumented function
    function visit(node) {
      // ---- call sites: obj.m(args) -> __dg.callm(obj, "m", [args]); f(args) -> __dg.callf(f, [args])
      if (ts.isCallExpression(node) && ctxStack.length > 0 && !node.questionDotToken) {
        const callee = node.expression;
        const args = node.arguments.map((a) => ts.visitNode(a, visit));
        const skip =
          callee.kind === ts.SyntaxKind.SuperKeyword || callee.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(callee) && (callee.text === "require" || callee.text === "__dg")) ||
          (ts.isPropertyAccessExpression(callee) && (callee.questionDotToken || (ts.isIdentifier(callee.expression) && callee.expression.text === "__dg"))) ||
          (ts.isPropertyAccessExpression(callee) && callee.expression.kind === ts.SyntaxKind.SuperKeyword) ||
          node.typeArguments;
        if (!skip) {
          const arr = f.createArrayLiteralExpression(args, false);
          if (ts.isPropertyAccessExpression(callee)) {
            const obj = ts.visitNode(callee.expression, visit);
            changed = true;
            return f.createCallExpression(f.createPropertyAccessExpression(DG, "callm"), undefined, [obj, f.createStringLiteral(callee.name.text), arr]);
          }
          if (ts.isElementAccessExpression(callee) && !callee.questionDotToken) {
            const obj = ts.visitNode(callee.expression, visit);
            const key = ts.visitNode(callee.argumentExpression, visit);
            changed = true;
            return f.createCallExpression(f.createPropertyAccessExpression(DG, "callm"), undefined, [obj, key, arr]);
          }
          if (ts.isIdentifier(callee) || ts.isParenthesizedExpression(callee)) {
            const fn = ts.visitNode(callee, visit);
            changed = true;
            return f.createCallExpression(f.createPropertyAccessExpression(DG, "callf"), undefined, [fn, arr]);
          }
        }
      }
      // ---- returns inside an instrumented function (not inside a nested function)
      if (ts.isReturnStatement(node) && ctxStack.length > 0) {
        const c = ctxStack[ctxStack.length - 1];
        const expr = node.expression ? ts.visitNode(node.expression, visit) : f.createIdentifier("undefined");
        changed = true;
        return f.updateReturnStatement(node, f.createCallExpression(f.createPropertyAccessExpression(DG, "ret"), undefined, [c, expr]));
      }
      // ---- function bodies
      if (isFunctionLike(node) && node.body) {
        const isAccessor = ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node);
        const isAsync = !!(node.modifiers && node.modifiers.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword));
        const isGen = !!node.asteriskToken;
        const isCtor = ts.isConstructorDeclaration(node);
        const useRun = (isAsync || isGen) && !isCtor;
        const sym = `js:${mod}.${qualname(node, sf)}`;
        const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
        const c = f.createUniqueName("__dgc");
        ctxStack.push(c);
        // visit the body with the new context
        let body = node.body;
        if (!ts.isBlock(body)) body = f.createBlock([f.createReturnStatement(body)], true);
        const visitedBody = ts.visitEachChild(body, visit, context);
        ctxStack.pop();
        const meta = f.createObjectLiteralExpression([
          f.createPropertyAssignment("sym", f.createStringLiteral(sym)),
          f.createPropertyAssignment("origin", f.createStringLiteral(ctxInfo.origin)),
          f.createPropertyAssignment("file", f.createStringLiteral(rel)),
          f.createPropertyAssignment("line", f.createNumericLiteral(String(line))),
          f.createPropertyAssignment("params", f.createArrayLiteralExpression(paramNames(node).map((n) => f.createStringLiteral(n)))),
        ]);
        const values = f.createArrayLiteralExpression(paramIdentifiers(node).map((n) => f.createIdentifier(n)));
        let newBody;
        if (useRun) {
          // return __dg.run(meta, [args], this, async/function* (c) { body })  (yield* for generators)
          const inner = isGen
            ? f.createFunctionExpression(isAsync ? [f.createModifier(ts.SyntaxKind.AsyncKeyword)] : undefined, f.createToken(ts.SyntaxKind.AsteriskToken), undefined, undefined, [f.createParameterDeclaration(undefined, undefined, c)], undefined, visitedBody)
            : f.createArrowFunction([f.createModifier(ts.SyntaxKind.AsyncKeyword)], undefined, [f.createParameterDeclaration(undefined, undefined, c)], undefined, undefined, visitedBody);
          const thisArg = ts.isArrowFunction(node) ? f.createIdentifier("undefined") : f.createThis();
          const call = f.createCallExpression(f.createPropertyAccessExpression(DG, "run"), undefined, [meta, values, thisArg, inner]);
          const stmt = isGen
            ? f.createReturnStatement(f.createYieldExpression(f.createToken(ts.SyntaxKind.AsteriskToken), call))
            : f.createReturnStatement(call);
          newBody = f.createBlock([stmt], true);
        } else {
          // const c = __dg.enter(meta, [args]); try { body } catch (e) { __dg.throwed(c, e); throw e } finally { __dg.exit(c) }
          const e = f.createUniqueName("__dge");
          const decl = f.createVariableStatement(undefined, f.createVariableDeclarationList([
            f.createVariableDeclaration(c, undefined, undefined, f.createCallExpression(f.createPropertyAccessExpression(DG, "enter"), undefined, [meta, values, (ts.isArrowFunction(node) || isCtor) ? f.createIdentifier("undefined") : f.createThis()])),
          ], ts.NodeFlags.Const));
          const tryStmt = f.createTryStatement(
            visitedBody,
            f.createCatchClause(f.createVariableDeclaration(e), f.createBlock([
              f.createExpressionStatement(f.createCallExpression(f.createPropertyAccessExpression(DG, "throwed"), undefined, [c, e])),
              f.createThrowStatement(e),
            ], true)),
            f.createBlock([f.createExpressionStatement(f.createCallExpression(f.createPropertyAccessExpression(DG, "exit"), undefined, [c]))], true),
          );
          newBody = f.createBlock([decl, tryStmt], true);
        }
        changed = true;
        if (ts.isFunctionDeclaration(node)) return f.updateFunctionDeclaration(node, node.modifiers, node.asteriskToken, node.name, node.typeParameters, node.parameters, node.type, newBody);
        if (ts.isFunctionExpression(node)) return f.updateFunctionExpression(node, node.modifiers, node.asteriskToken, node.name, node.typeParameters, node.parameters, node.type, newBody);
        if (ts.isArrowFunction(node)) return f.updateArrowFunction(node, node.modifiers, node.typeParameters, node.parameters, node.type, node.equalsGreaterThanToken, newBody);
        if (ts.isMethodDeclaration(node)) return f.updateMethodDeclaration(node, node.modifiers, node.asteriskToken, node.name, node.questionToken, node.typeParameters, node.parameters, node.type, newBody);
        if (ts.isConstructorDeclaration(node)) return f.updateConstructorDeclaration(node, node.modifiers, node.parameters, newBody);
        if (isAccessor) {
          if (ts.isGetAccessorDeclaration(node)) return f.updateGetAccessorDeclaration(node, node.modifiers, node.name, node.parameters, node.type, newBody);
          return f.updateSetAccessorDeclaration(node, node.modifiers, node.name, node.parameters, newBody);
        }
      }
      return ts.visitEachChild(node, visit, context);
    }
    return (root) => {
      const visited = ts.visitNode(root, visit);
      // Register named top-level classes so the runtime can claim overriding fakes by
      // prototype identity: __dg.registerClass(Name, "js:<module>.Name").
      const extra = [];
      for (const stmt of visited.statements) {
        if (ts.isClassDeclaration(stmt) && stmt.name) {
          const sym = `js:${mod}.${stmt.name.text}`;
          extra.push({ after: stmt, stmt: f.createExpressionStatement(f.createCallExpression(f.createPropertyAccessExpression(DG, "registerClass"), undefined, [f.createIdentifier(stmt.name.text), f.createStringLiteral(sym), f.createStringLiteral(ctxInfo.origin)])) });
        }
      }
      if (extra.length === 0) return visited;
      const statements = [];
      for (const stmt of visited.statements) {
        statements.push(stmt);
        for (const e of extra) if (e.after === stmt) { statements.push(e.stmt); changed = true; }
      }
      return f.updateSourceFile(visited, statements);
    };
  };

  const result = ts.transform(sf, [transformer]);
  const out = result.transformed[0];
  if (!changed) return false;
  const printer = ts.createPrinter({ newLine: ts.NewLineKind.LineFeed, removeComments: false });
  let printed = printer.printFile(out);
  const header = `const __dg = require(${JSON.stringify(ctxInfo.runtime)});\n`;
  // Keep a leading shebang / 'use strict' / reflect-metadata import order intact enough:
  // our require is side-effect free, so putting it first is safe.
  printed = header + printed;
  if (!ctxInfo.dry) fs.writeFileSync(file, printed);
  return true;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = path.resolve(args.root);
  const index = [];
  let count = 0;
  const seen = new Set();
  const roots = [...args.tests.map((d) => ({ dir: path.resolve(root, d), origin: "test" })), ...args.src.map((d) => ({ dir: path.resolve(root, d), origin: "repo" }))];
  for (const r of roots) {
    if (!fs.existsSync(r.dir)) continue;
    for (const file of walk(r.dir)) {
      if (seen.has(file)) continue;
      seen.add(file);
      try {
        if (instrumentFile(file, { root, origin: r.origin, runtime: path.resolve(args.runtime), dry: args.dry }, index)) count++;
      } catch (e) {
        process.stderr.write(`diffgenome: failed to instrument ${file}: ${e.message}\n`);
      }
    }
  }
  if (args.index) fs.writeFileSync(args.index, JSON.stringify({ root: root, definitions: index }, null, 1) + "\n");
  process.stdout.write(`instrumented ${count} files, indexed ${index.length} definitions\n`);
}

main();
