package main

// Branch-site wrapping and the neutral-IR front end (see src/diffgenome/dependence.py).
// Both read positions from the ORIGINAL parse, before any rewriting, so a site id is the
// same whether it is computed here at instrumentation time or by the facts pass.

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"go/ast"
	"go/token"
)

// siteID must stay identical to diffgenome.sites.site_id.
func siteID(rel string, fset *token.FileSet, cond ast.Expr) (string, []int) {
	a, b := fset.Position(cond.Pos()), fset.Position(cond.End())
	span := []int{a.Line, a.Column, b.Line, b.Column}
	h := sha256.Sum256([]byte(fmt.Sprintf("%s:%d:%d:%d:%d", rel, span[0], span[1], span[2], span[3])))
	return "br:" + hex.EncodeToString(h[:])[:12], span
}

// wrapBranches rewrites every `if cond {` in repo code to `if dg.Branch("<site>", cond) {`.
// Ids are computed before the rewrite, from original positions.
func (fc *fileCtx) wrapBranches(f *ast.File) {
	type pending struct {
		s  *ast.IfStmt
		id string
	}
	var todo []pending
	ast.Inspect(f, func(n ast.Node) bool {
		if s, ok := n.(*ast.IfStmt); ok && s.Cond != nil {
			id, _ := siteID(fc.rel, fc.fset, s.Cond)
			todo = append(todo, pending{s, id})
		}
		return true
	})
	for _, p := range todo {
		p.s.Cond = &ast.CallExpr{Fun: sel("dg", "Branch"), Args: []ast.Expr{strLit(p.id), p.s.Cond}}
		fc.changed = true
	}
}

// ---- neutral IR

type irFn = map[string]any

func (fc *fileCtx) lowerFuncs(f *ast.File) []irFn {
	var out []irFn
	for _, d := range f.Decls {
		fd, ok := d.(*ast.FuncDecl)
		if !ok || fd.Body == nil {
			continue
		}
		qual := fd.Name.Name
		var params []string
		if fd.Recv != nil && len(fd.Recv.List) > 0 {
			if rt := receiverType(fd.Recv.List[0].Type); rt != "" {
				qual = rt + "." + fd.Name.Name
			}
			for _, n := range fd.Recv.List[0].Names {
				params = append(params, n.Name)
			}
		}
		if fd.Type.Params != nil {
			for _, fl := range fd.Type.Params.List {
				for _, n := range fl.Names {
					params = append(params, n.Name)
				}
			}
		}
		if params == nil {
			params = []string{}
		}
		out = append(out, irFn{"symbol": fc.symbolFor(qual), "file": fc.rel, "params": params, "body": fc.lowerBlock(fd.Body.List)})
	}
	return out
}

func (fc *fileCtx) line(n ast.Node) int { return fc.fset.Position(n.Pos()).Line }

// path returns the dotted access path of an ident/selector chain, or "".
func path(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.SelectorExpr:
		if b := path(x.X); b != "" {
			return b + "." + x.Sel.Name
		}
	case *ast.ParenExpr:
		return path(x.X)
	case *ast.StarExpr:
		return path(x.X)
	}
	return ""
}

type exprFacts struct {
	uses  []string
	calls []map[string]any
}

func (fc *fileCtx) expr(e ast.Expr) exprFacts {
	var ef exprFacts
	seen := map[string]bool{}
	add := func(p string) {
		if p != "" && p != "_" && p != "nil" && p != "true" && p != "false" && !seen[p] {
			seen[p] = true
			ef.uses = append(ef.uses, p)
		}
	}
	var walk func(e ast.Expr)
	walk = func(e ast.Expr) {
		switch x := e.(type) {
		case nil:
		case *ast.Ident, *ast.SelectorExpr:
			if p := path(x); p != "" {
				add(p)
				return
			}
			if s, ok := x.(*ast.SelectorExpr); ok {
				walk(s.X)
			}
		case *ast.CallExpr:
			if s, ok := x.Fun.(*ast.SelectorExpr); ok {
				if p := path(s.X); p != "" {
					add(p)
				} else {
					walk(s.X)
				}
			}
			args := [][]string{}
			addr := []string{}
			for _, a := range x.Args {
				sub := fc.expr(a)
				if len(sub.uses) == 0 {
					sub.uses = []string{"?"}
				}
				args = append(args, sub.uses)
				for _, u := range sub.uses {
					if u != "?" {
						add(u)
					}
				}
				ef.calls = append(ef.calls, sub.calls...)
				if ue, ok := a.(*ast.UnaryExpr); ok && ue.Op == token.AND {
					if id, ok := ue.X.(*ast.Ident); ok {
						addr = append(addr, id.Name)
					}
				}
			}
			ef.calls = append(ef.calls, map[string]any{"callee": exprString(x.Fun), "args": args, "line": fc.line(x), "addr": addr})
		case *ast.UnaryExpr:
			walk(x.X)
		case *ast.BinaryExpr:
			walk(x.X)
			walk(x.Y)
		case *ast.ParenExpr:
			walk(x.X)
		case *ast.StarExpr:
			walk(x.X)
		case *ast.IndexExpr:
			walk(x.X)
			walk(x.Index)
		case *ast.TypeAssertExpr:
			walk(x.X)
		case *ast.CompositeLit:
			for _, el := range x.Elts {
				if kv, ok := el.(*ast.KeyValueExpr); ok {
					walk(kv.Value)
				} else {
					walk(el)
				}
			}
		case *ast.KeyValueExpr:
			walk(x.Value)
		case *ast.SliceExpr:
			walk(x.X)
		case *ast.FuncLit, *ast.BasicLit:
		}
	}
	walk(e)
	if ef.uses == nil {
		ef.uses = []string{}
	}
	if ef.calls == nil {
		ef.calls = []map[string]any{}
	}
	return ef
}

func (fc *fileCtx) exprs(es []ast.Expr) exprFacts {
	var out exprFacts
	out.uses, out.calls = []string{}, []map[string]any{}
	for _, e := range es {
		f := fc.expr(e)
		out.uses = append(out.uses, f.uses...)
		out.calls = append(out.calls, f.calls...)
	}
	return out
}

func (fc *fileCtx) lowerBlock(stmts []ast.Stmt) []map[string]any {
	out := []map[string]any{}
	for _, s := range stmts {
		out = append(out, fc.lowerStmt(s)...)
	}
	return out
}

func (fc *fileCtx) lowerStmt(s ast.Stmt) []map[string]any {
	line := fc.line(s)
	switch x := s.(type) {
	case *ast.AssignStmt:
		f := fc.exprs(x.Rhs)
		defs, stores := []string{}, []string{}
		for _, l := range x.Lhs {
			if id, ok := l.(*ast.Ident); ok {
				defs = append(defs, id.Name) // "_" kept: it holds a result position
			} else if p := path(l); p != "" {
				stores = append(stores, p)
			} else if ix, ok := l.(*ast.IndexExpr); ok {
				stores = append(stores, path(ix.X)+"[]")
			} else {
				stores = append(stores, "?")
			}
		}
		if x.Tok != token.ASSIGN && x.Tok != token.DEFINE { // op-assign reads its target
			f.uses = append(f.uses, defs...)
			f.uses = append(f.uses, stores...)
		}
		rhs := x.Rhs[0]
		for {
			if ta, ok := rhs.(*ast.TypeAssertExpr); ok {
				rhs = ta.X
			} else if pe, ok := rhs.(*ast.ParenExpr); ok {
				rhs = pe.X
			} else {
				break
			}
		}
		_, isCall := rhs.(*ast.CallExpr)
		return []map[string]any{{"k": "assign", "line": line, "defs": defs, "stores": stores, "uses": f.uses, "calls": f.calls, "value_is_call": len(x.Rhs) == 1 && isCall}}
	case *ast.IncDecStmt:
		p := path(x.X)
		if id, ok := x.X.(*ast.Ident); ok {
			return []map[string]any{{"k": "assign", "line": line, "defs": []string{id.Name}, "stores": []string{}, "uses": []string{p}, "calls": []map[string]any{}}}
		}
		return []map[string]any{{"k": "assign", "line": line, "defs": []string{}, "stores": []string{p}, "uses": []string{p}, "calls": []map[string]any{}}}
	case *ast.DeclStmt:
		out := []map[string]any{}
		if gd, ok := x.Decl.(*ast.GenDecl); ok {
			for _, sp := range gd.Specs {
				if vs, ok := sp.(*ast.ValueSpec); ok {
					defs := []string{}
					for _, n := range vs.Names {
						defs = append(defs, n.Name)
					}
					f := fc.exprs(vs.Values)
					out = append(out, map[string]any{"k": "assign", "line": line, "defs": defs, "stores": []string{}, "uses": f.uses, "calls": f.calls})
				}
			}
		}
		return out
	case *ast.ExprStmt:
		f := fc.expr(x.X)
		if c, ok := x.X.(*ast.CallExpr); ok {
			if id, ok := c.Fun.(*ast.Ident); ok && id.Name == "panic" {
				return []map[string]any{{"k": "raise", "line": line, "uses": f.uses, "calls": f.calls}}
			}
		}
		return []map[string]any{{"k": "expr", "line": line, "uses": f.uses, "calls": f.calls}}
	case *ast.IfStmt:
		out := []map[string]any{}
		if x.Init != nil {
			out = append(out, fc.lowerStmt(x.Init)...)
		}
		id, span := siteID(fc.rel, fc.fset, x.Cond)
		f := fc.expr(x.Cond)
		var els []map[string]any
		switch e := x.Else.(type) {
		case *ast.BlockStmt:
			els = fc.lowerBlock(e.List)
		case *ast.IfStmt:
			els = fc.lowerStmt(e)
		default:
			els = []map[string]any{}
		}
		out = append(out, map[string]any{"k": "if", "line": line, "site": id, "span": span, "pred": exprString(x.Cond),
			"uses": f.uses, "calls": f.calls, "then": fc.lowerBlock(x.Body.List), "else": els})
		return out
	case *ast.ReturnStmt:
		f := fc.exprs(x.Results)
		return []map[string]any{{"k": "return", "line": line, "uses": f.uses, "calls": f.calls}}
	case *ast.BlockStmt:
		return fc.lowerBlock(x.List)
	case *ast.LabeledStmt:
		return fc.lowerStmt(x.Stmt)
	case *ast.ForStmt:
		f := fc.expr(x.Cond)
		body := []map[string]any{}
		if x.Init != nil {
			body = append(body, fc.lowerStmt(x.Init)...)
		}
		body = append(body, fc.lowerBlock(x.Body.List)...)
		return []map[string]any{{"k": "loop", "line": line, "uses": f.uses, "calls": f.calls, "defs": []string{}, "body": body}}
	case *ast.RangeStmt:
		f := fc.expr(x.X)
		defs := []string{}
		for _, e := range []ast.Expr{x.Key, x.Value} {
			if id, ok := e.(*ast.Ident); ok && id.Name != "_" {
				defs = append(defs, id.Name)
			}
		}
		return []map[string]any{{"k": "loop", "line": line, "uses": f.uses, "calls": f.calls, "defs": defs, "body": fc.lowerBlock(x.Body.List)}}
	case *ast.BranchStmt:
		return []map[string]any{{"k": "break", "line": line}}
	case *ast.SwitchStmt, *ast.TypeSwitchStmt, *ast.SelectStmt:
		blocks := [][]map[string]any{}
		var body *ast.BlockStmt
		reason := "switch"
		switch y := x.(type) {
		case *ast.SwitchStmt:
			body = y.Body
		case *ast.TypeSwitchStmt:
			body, reason = y.Body, "type-switch"
		case *ast.SelectStmt:
			body, reason = y.Body, "select"
		}
		for _, c := range body.List {
			switch cc := c.(type) {
			case *ast.CaseClause:
				blocks = append(blocks, fc.lowerBlock(cc.Body))
			case *ast.CommClause:
				blocks = append(blocks, fc.lowerBlock(cc.Body))
			}
		}
		return []map[string]any{{"k": "opaque", "line": line, "reason": reason, "blocks": blocks}}
	case *ast.DeferStmt:
		return []map[string]any{{"k": "opaque", "line": line, "reason": "defer"}}
	case *ast.GoStmt:
		return []map[string]any{{"k": "opaque", "line": line, "reason": "go"}}
	}
	return []map[string]any{{"k": "opaque", "line": line, "reason": fmt.Sprintf("%T", s)}}
}
