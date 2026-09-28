// diffgenome Go source instrumenter.
//
//	go run ./instrument -root <repo copy> -module <module path> -src <dir>[,dir] -tests <dir>[,dir] -index <out.json>
//
// Rewrites every .go file under the roots IN PLACE (the copy is disposable): each function
// or method body reports entry (dg.Enter with its parameters), and a deferred function
// reports the results, a trailing error, or a panic (dg.Exit / dg.Panic). Unnamed results
// are named so the defer can read them. Test functions and t.Run subtests become stimuli
// (dg.Begin / dg.End). Files under a test root, *_test.go files and generated mock packages
// are "test" origin; a MockGen file's "Source: <pkg> (interfaces: X)" header gives each
// mock method a deterministic claim on the in-repo definer of that interface method.
//
// Symbol naming: go:<package dir relative to root>.<Recv.Func>; closures are <anon>@line.
// It also writes the definition index the Python side uses for diff mapping and context.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type definition struct {
	Symbol string `json:"symbol"`
	Path   string `json:"path"`
	Start  int    `json:"start"`
	End    int    `json:"end"`
	Kind   string `json:"kind"`
}

type root struct {
	dir    string
	origin string
}

var mockSource = regexp.MustCompile(`Source: (\S+) \(interfaces: ([^)]+)\)`)

func main() {
	rootFlag := flag.String("root", "", "repository copy")
	module := flag.String("module", "", "module path of the repository")
	srcFlag := flag.String("src", ".", "comma-separated source dirs (repo origin)")
	testFlag := flag.String("tests", "", "comma-separated test dirs (test origin), e.g. db/mock")
	indexFlag := flag.String("index", "", "definition index output")
	flag.Parse()
	if *rootFlag == "" || *module == "" {
		fmt.Fprintln(os.Stderr, "-root and -module are required")
		os.Exit(2)
	}
	absRoot, _ := filepath.Abs(*rootFlag)
	var roots []root
	for _, d := range strings.Split(*testFlag, ",") {
		if d != "" {
			roots = append(roots, root{filepath.Join(absRoot, d), "test"})
		}
	}
	for _, d := range strings.Split(*srcFlag, ",") {
		if d != "" {
			roots = append(roots, root{filepath.Join(absRoot, d), "repo"})
		}
	}
	// method definers per package dir: pkgdir -> method name -> []type
	definers := collectDefiners(absRoot)
	var index []definition
	seen := map[string]bool{}
	count := 0
	for _, r := range roots {
		filepath.Walk(r.dir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			name := info.Name()
			if info.IsDir() {
				if strings.HasPrefix(name, ".") || name == "vendor" || name == "testdata" || name == "node_modules" || path == filepath.Join(absRoot, "internal", "diffgenome") {
					return filepath.SkipDir
				}
				return nil
			}
			if !strings.HasSuffix(name, ".go") || seen[path] {
				return nil
			}
			seen[path] = true
			origin := r.origin
			if strings.HasSuffix(name, "_test.go") {
				origin = "test"
			}
			changed, defs, err := instrumentFile(absRoot, *module, path, origin, definers)
			if err != nil {
				fmt.Fprintf(os.Stderr, "diffgenome: %s: %v\n", path, err)
				return nil
			}
			index = append(index, defs...)
			if changed {
				count++
			}
			return nil
		})
	}
	if *indexFlag != "" {
		sort.Slice(index, func(i, j int) bool { return index[i].Path < index[j].Path || (index[i].Path == index[j].Path && index[i].Start < index[j].Start) })
		data, _ := json.MarshalIndent(map[string]any{"root": absRoot, "definitions": index}, "", " ")
		_ = os.WriteFile(*indexFlag, append(data, '\n'), 0o644)
	}
	fmt.Printf("instrumented %d files, indexed %d definitions\n", count, len(index))
}

// collectDefiners maps, per package directory, each method name to the receiver types
// defining it, so a mocked interface method can be claimed on its sole in-repo definer.
func collectDefiners(absRoot string) map[string]map[string][]string {
	out := map[string]map[string][]string{}
	filepath.Walk(absRoot, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			if info != nil && info.IsDir() && (strings.HasPrefix(info.Name(), ".") || info.Name() == "vendor" || info.Name() == "node_modules") {
				return filepath.SkipDir
			}
			return nil
		}
		fset := token.NewFileSet()
		f, perr := parser.ParseFile(fset, path, nil, 0)
		if perr != nil {
			return nil
		}
		pkgDir, _ := filepath.Rel(absRoot, filepath.Dir(path))
		pkgDir = filepath.ToSlash(pkgDir)
		if _, ok := out[pkgDir]; !ok {
			out[pkgDir] = map[string][]string{}
		}
		for _, d := range f.Decls {
			fd, ok := d.(*ast.FuncDecl)
			if !ok || fd.Recv == nil || len(fd.Recv.List) == 0 {
				continue
			}
			rt := receiverType(fd.Recv.List[0].Type)
			if rt == "" || strings.HasPrefix(rt, "Mock") {
				continue
			}
			out[pkgDir][fd.Name.Name] = appendUnique(out[pkgDir][fd.Name.Name], rt)
		}
		return nil
	})
	return out
}

func appendUnique(xs []string, x string) []string {
	for _, y := range xs {
		if y == x {
			return xs
		}
	}
	return append(xs, x)
}

func receiverType(e ast.Expr) string {
	switch t := e.(type) {
	case *ast.StarExpr:
		return receiverType(t.X)
	case *ast.Ident:
		return t.Name
	case *ast.IndexExpr:
		return receiverType(t.X)
	case *ast.IndexListExpr:
		return receiverType(t.X)
	}
	return ""
}

type fileCtx struct {
	fset       *token.FileSet
	rel        string
	pkgDir     string
	origin     string
	module     string
	mockPkgDir string // package dir of the mocked interfaces, if this is a MockGen file
	mockIfaces map[string]bool
	definers   map[string]map[string][]string
	index      *[]definition
	changed    bool
}

func instrumentFile(absRoot, module, path, origin string, definers map[string]map[string][]string) (bool, []definition, error) {
	src, err := os.ReadFile(path)
	if err != nil {
		return false, nil, err
	}
	if bytes.Contains(src, []byte("internal/diffgenome/dg\"")) {
		return false, nil, nil // already instrumented (re-runs after adding a probe file)
	}
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, path, src, parser.ParseComments)
	if err != nil {
		return false, nil, err
	}
	rel, _ := filepath.Rel(absRoot, path)
	rel = filepath.ToSlash(rel)
	pkgDir := filepath.ToSlash(filepath.Dir(rel))
	if pkgDir == "." {
		pkgDir = ""
	}
	fc := &fileCtx{fset: fset, rel: rel, pkgDir: pkgDir, origin: origin, module: module, definers: definers}
	// MockGen header -> claims for mock methods
	if bytes.Contains(src, []byte("Code generated by MockGen")) {
		if m := mockSource.FindSubmatch(src); m != nil {
			srcPkg := string(m[1])
			fc.mockPkgDir = strings.TrimPrefix(strings.TrimPrefix(srcPkg, module), "/")
			fc.mockIfaces = map[string]bool{}
			for _, name := range strings.Split(string(m[2]), ",") {
				fc.mockIfaces[strings.TrimSpace(name)] = true
			}
		}
		origin = "test"
		fc.origin = "test"
	}
	var defs []definition
	fc.index = &defs
	// type declarations for the index (enclosing "class" lookups)
	for _, d := range f.Decls {
		if gd, ok := d.(*ast.GenDecl); ok && gd.Tok == token.TYPE {
			for _, s := range gd.Specs {
				if ts, ok := s.(*ast.TypeSpec); ok {
					defs = append(defs, definition{Symbol: fc.symbolFor(ts.Name.Name), Path: rel, Start: fset.Position(ts.Pos()).Line, End: fset.Position(ts.End()).Line, Kind: "class"})
				}
			}
		}
	}
	for _, d := range f.Decls {
		if fd, ok := d.(*ast.FuncDecl); ok && fd.Body != nil {
			fc.instrumentFunc(fd)
		}
	}
	// closures anywhere (including inside already-instrumented bodies)
	ast.Inspect(f, func(n ast.Node) bool {
		if fl, ok := n.(*ast.FuncLit); ok && fl.Body != nil {
			fc.instrumentLit(fl)
		}
		return true
	})
	if !fc.changed {
		return false, defs, nil
	}
	var buf bytes.Buffer
	if err := format.Node(&buf, fset, f); err != nil {
		return false, defs, err
	}
	out := addImport(buf.String(), module+"/internal/diffgenome/dg")
	if err := os.WriteFile(path, []byte(out), 0o644); err != nil {
		return false, defs, err
	}
	return true, defs, nil
}

func (fc *fileCtx) symbolFor(qual string) string {
	if fc.pkgDir == "" {
		return "go:" + qual
	}
	return "go:" + fc.pkgDir + "." + qual
}

var anonStack []string // qualname stack for closures

func (fc *fileCtx) instrumentFunc(fd *ast.FuncDecl) {
	qual := fd.Name.Name
	if fd.Recv != nil && len(fd.Recv.List) > 0 {
		if rt := receiverType(fd.Recv.List[0].Type); rt != "" {
			qual = rt + "." + fd.Name.Name
		}
	}
	sym := fc.symbolFor(qual)
	line := fc.fset.Position(fd.Pos()).Line
	*fc.index = append(*fc.index, definition{Symbol: sym, Path: fc.rel, Start: line, End: fc.fset.Position(fd.End()).Line, Kind: "function"})
	claim, relation := "", ""
	if fc.mockIfaces != nil && fd.Recv != nil {
		rt := receiverType(fd.Recv.List[0].Type)
		iface := strings.TrimPrefix(rt, "Mock")
		if fc.mockIfaces[iface] && !strings.HasSuffix(rt, "MockRecorder") {
			if defs := fc.definers[fc.mockPkgDir][fd.Name.Name]; len(defs) == 1 {
				claim = "go:" + fc.mockPkgDir + "." + defs[0] + "." + fd.Name.Name
				relation = "mocks-interface:" + iface
			} else if len(defs) > 1 {
				claim = "go:" + fc.mockPkgDir + "." + iface + "." + fd.Name.Name
				relation = "mocks-interface:" + iface + ";candidates=" + strings.Join(defs, "|")
			}
		}
	}
	fc.wrapBody(fd.Type, fd.Body, sym, line, claim, relation, isTestFunc(fd))
	fc.markLits(fd.Body, qual)
}

func isTestFunc(fd *ast.FuncDecl) bool {
	if fd.Recv != nil || !strings.HasPrefix(fd.Name.Name, "Test") || fd.Type.Params == nil || len(fd.Type.Params.List) != 1 {
		return false
	}
	return exprString(fd.Type.Params.List[0].Type) == "*testing.T"
}

func isSubtestLit(fl *ast.FuncLit) bool {
	if fl.Type.Params == nil || len(fl.Type.Params.List) != 1 {
		return false
	}
	return exprString(fl.Type.Params.List[0].Type) == "*testing.T"
}

func exprString(e ast.Expr) string {
	var b bytes.Buffer
	_ = format.Node(&b, token.NewFileSet(), e)
	return b.String()
}

var litQual = map[*ast.FuncLit]string{}

func (fc *fileCtx) markLits(body *ast.BlockStmt, qual string) {
	ast.Inspect(body, func(n ast.Node) bool {
		if fl, ok := n.(*ast.FuncLit); ok {
			if _, done := litQual[fl]; !done {
				litQual[fl] = qual + ".<anon>@" + strconv.Itoa(fc.fset.Position(fl.Pos()).Line)
			}
		}
		return true
	})
}

var litDone = map[*ast.FuncLit]bool{}

func (fc *fileCtx) instrumentLit(fl *ast.FuncLit) {
	if litDone[fl] {
		return
	}
	litDone[fl] = true
	line := fc.fset.Position(fl.Pos()).Line
	qual, ok := litQual[fl]
	if !ok {
		qual = "<anon>@" + strconv.Itoa(line)
	}
	sym := fc.symbolFor(qual)
	*fc.index = append(*fc.index, definition{Symbol: sym, Path: fc.rel, Start: line, End: fc.fset.Position(fl.End()).Line, Kind: "function"})
	fc.wrapBody(fl.Type, fl.Body, sym, line, "", "", isSubtestLit(fl) && fc.origin == "test")
	fc.markLits(fl.Body, qual)
}

// wrapBody prepends the entry call and the deferred exit to a function body.
func (fc *fileCtx) wrapBody(ft *ast.FuncType, body *ast.BlockStmt, sym string, line int, claim, relation string, stimulus bool) {
	// name unnamed results so the defer can read them
	var resultNames []ast.Expr
	if ft.Results != nil {
		idx := 0
		for _, field := range ft.Results.List {
			if len(field.Names) == 0 {
				name := ast.NewIdent(fmt.Sprintf("__dgr%d", idx))
				field.Names = []*ast.Ident{name}
				resultNames = append(resultNames, ast.NewIdent(name.Name))
				idx++
				continue
			}
			for _, n := range field.Names {
				if n.Name == "_" {
					n.Name = fmt.Sprintf("__dgr%d", idx)
				}
				resultNames = append(resultNames, ast.NewIdent(n.Name))
				idx++
			}
		}
	}
	// parameters
	var paramNames []string
	var paramValues []ast.Expr
	if ft.Params != nil {
		for _, field := range ft.Params.List {
			for _, n := range field.Names {
				if n.Name == "_" {
					continue
				}
				paramNames = append(paramNames, n.Name)
				paramValues = append(paramValues, ast.NewIdent(n.Name))
			}
		}
	}
	metaElts := []ast.Expr{
		kv("Sym", strLit(sym)), kv("Origin", strLit(fc.origin)), kv("File", strLit(fc.rel)),
		kv("Line", &ast.BasicLit{Kind: token.INT, Value: strconv.Itoa(line)}),
		kv("Params", &ast.CompositeLit{Type: &ast.ArrayType{Elt: ast.NewIdent("string")}, Elts: strLits(paramNames)}),
	}
	if claim != "" {
		metaElts = append(metaElts, kv("Claim", strLit(claim)), kv("Relation", strLit(relation)))
	}
	meta := &ast.CompositeLit{Type: sel("dg", "Meta"), Elts: metaElts}
	enterArgs := append([]ast.Expr{meta}, paramValues...)
	enter := &ast.AssignStmt{
		Lhs: []ast.Expr{ast.NewIdent("__dgc")}, Tok: token.DEFINE,
		Rhs: []ast.Expr{&ast.CallExpr{Fun: sel("dg", "Enter"), Args: enterArgs}},
	}
	exitArgs := append([]ast.Expr{ast.NewIdent("__dgc")}, resultNames...)
	deferBody := &ast.BlockStmt{List: []ast.Stmt{
		&ast.IfStmt{
			Init: &ast.AssignStmt{Lhs: []ast.Expr{ast.NewIdent("__dgp")}, Tok: token.DEFINE, Rhs: []ast.Expr{&ast.CallExpr{Fun: ast.NewIdent("recover")}}},
			Cond: &ast.BinaryExpr{X: ast.NewIdent("__dgp"), Op: token.NEQ, Y: ast.NewIdent("nil")},
			Body: &ast.BlockStmt{List: []ast.Stmt{
				&ast.ExprStmt{X: &ast.CallExpr{Fun: sel("dg", "Panic"), Args: []ast.Expr{ast.NewIdent("__dgc"), ast.NewIdent("__dgp")}}},
				&ast.ExprStmt{X: &ast.CallExpr{Fun: ast.NewIdent("panic"), Args: []ast.Expr{ast.NewIdent("__dgp")}}},
			}},
			Else: &ast.BlockStmt{List: []ast.Stmt{
				&ast.ExprStmt{X: &ast.CallExpr{Fun: sel("dg", "Exit"), Args: exitArgs}},
			}},
		},
	}}
	deferStmt := &ast.DeferStmt{Call: &ast.CallExpr{Fun: &ast.FuncLit{Type: &ast.FuncType{Params: &ast.FieldList{}}, Body: deferBody}}}
	litDone[deferStmt.Call.Fun.(*ast.FuncLit)] = true
	stmts := []ast.Stmt{enter, deferStmt}
	if stimulus {
		// dg.Begin(t.Name()); defer func() { dg.End(t.Failed()) }()
		tname := ft.Params.List[0].Names[0].Name
		begin := &ast.ExprStmt{X: &ast.CallExpr{Fun: sel("dg", "Begin"), Args: []ast.Expr{&ast.CallExpr{Fun: sel(tname, "Name")}}}}
		endLit := &ast.FuncLit{Type: &ast.FuncType{Params: &ast.FieldList{}}, Body: &ast.BlockStmt{List: []ast.Stmt{
			&ast.ExprStmt{X: &ast.CallExpr{Fun: sel("dg", "End"), Args: []ast.Expr{&ast.CallExpr{Fun: sel(tname, "Failed")}}}},
		}}}
		litDone[endLit] = true
		end := &ast.DeferStmt{Call: &ast.CallExpr{Fun: endLit}}
		stmts = []ast.Stmt{begin, end, enter, deferStmt}
	}
	body.List = append(stmts, body.List...)
	fc.changed = true
}

func kv(k string, v ast.Expr) ast.Expr { return &ast.KeyValueExpr{Key: ast.NewIdent(k), Value: v} }
func strLit(s string) ast.Expr           { return &ast.BasicLit{Kind: token.STRING, Value: strconv.Quote(s)} }
func sel(x, name string) ast.Expr        { return &ast.SelectorExpr{X: ast.NewIdent(x), Sel: ast.NewIdent(name)} }
func strLits(xs []string) []ast.Expr {
	out := make([]ast.Expr, 0, len(xs))
	for _, x := range xs {
		out = append(out, strLit(x))
	}
	return out
}

// addImport inserts the dg import after the package clause (gofmt-compatible enough).
func addImport(src, path string) string {
	idx := strings.Index(src, "\npackage ")
	if idx < 0 && strings.HasPrefix(src, "package ") {
		idx = 0
	} else if idx >= 0 {
		idx++
	} else {
		return src
	}
	end := strings.Index(src[idx:], "\n")
	if end < 0 {
		return src
	}
	insert := "\n\nimport dg " + strconv.Quote(path) + "\n"
	return src[:idx+end] + insert + src[idx+end:]
}
