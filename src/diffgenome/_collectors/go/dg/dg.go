// Package dg is the diffgenome Go runtime: instrumented code reports function entry,
// exit (results or panic) and test stimuli here, and one Execution (the diffgenome event
// protocol, JSON) is written per test or subtest. Copied into the workspace copy of the
// target as <module>/internal/diffgenome/dg so no network or module changes are needed.
//
// Attribution: per-goroutine call stacks keyed by goroutine id. Goroutines spawned by
// instrumented code start with no parent (their calls hang off the stimulus root); spawn
// causality is recorded as a limitation, not guessed.
package dg

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
)

const (
	maxArgs     = 8
	digestDepth = 3
	digestWidth = 16
)

// Meta is what the instrumenter knows statically about a function.
type Meta struct {
	Sym      string
	Origin   string // "repo" | "test"
	File     string
	Line     int
	Params   []string
	Claim    string // for test doubles: the in-repo symbol this method stands in for
	Relation string // how Claim was established, e.g. "mocks-interface:Store"
	Recv     any    // the receiver, for state facts (nil for functions)
}

type symbol struct {
	ID       string    `json:"id"`
	Origin   string    `json:"origin"`
	Location *location `json:"location"`
}

type location struct {
	Path string `json:"path"`
	Line int    `json:"line"`
}

type node struct {
	Type      string      `json:"type"`
	ID        int         `json:"id"`
	Parent    *int        `json:"parent"`
	Symbol    string      `json:"symbol,omitempty"`
	Collector int         `json:"collector"`
	Args      [][3]string `json:"args"`
	Thread    int         `json:"thread,omitempty"`
	Outcome   string      `json:"outcome"`
	Result    string      `json:"result"`
	// substitution fields (present only on substitution nodes; see MarshalJSON)
	Mechanism  string      `json:"mechanism,omitempty"`
	Substitute string      `json:"substitute,omitempty"`
	Claimed    *string     `json:"-"`
	Relation   string      `json:"relation,omitempty"`
	Path       []string    `json:"-"`
	State      [][3]string `json:"-"`
	StateAfter [][3]string `json:"-"`
}

// MarshalJSON emits exactly the protocol's fields for each node type.
func (n *node) MarshalJSON() ([]byte, error) {
	m := map[string]any{"type": n.Type, "id": n.ID, "parent": n.Parent, "collector": n.Collector,
		"args": n.Args, "outcome": n.Outcome, "result": n.Result, "state": n.State}
	if n.Args == nil {
		m["args"] = [][3]string{}
	}
	if n.State == nil {
		m["state"] = [][3]string{}
	}
	if n.Type == "call" {
		m["symbol"] = n.Symbol
		m["thread"] = n.Thread
		sa := n.StateAfter
		if sa == nil {
			sa = [][3]string{}
		}
		m["state_after"] = sa
	} else {
		m["mechanism"] = n.Mechanism
		m["substitute"] = n.Substitute
		m["claimed_target"] = n.Claimed
		m["relation"] = n.Relation
		p := n.Path
		if p == nil {
			p = []string{}
		}
		m["path"] = p
	}
	return json.Marshal(m)
}

type branchObs struct {
	Site    string `json:"site"`
	Outcome bool   `json:"outcome"`
	Node    int    `json:"node"`
	Seq     int    `json:"seq"`
}

type execution struct {
	ref       string
	nodes     []*node
	branches  []branchObs
	symbols   map[string]symbol
	stacks    map[int64][]int // goroutine id -> node ids
	goroutine map[int64]int   // goroutine id -> thread number
}

// Ctx is returned by Enter and consumed by Exit/Panic.
type Ctx struct {
	id   int
	sub  int // substitution wrapper node id, or -1
	gid  int64
	exec *execution
	recv any // receiver, for the state view on exit
}

var (
	mu     sync.Mutex
	active []*execution
	outDir = os.Getenv("DIFFGENOME_OUT")
	stim   = envOr("DIFFGENOME_STIMULUS", "existing_test")
	rev    = os.Getenv("DIFFGENOME_REVISION")
)

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func goid() int64 {
	var buf [64]byte
	n := runtime.Stack(buf[:], false)
	fields := bytes.Fields(buf[:n])
	if len(fields) >= 2 {
		id, _ := strconv.ParseInt(string(fields[1]), 10, 64)
		return id
	}
	return 0
}

// ----------------------------------------------------------------------------- summaries

func shape(v any) string {
	if v == nil {
		return "nil"
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Slice, reflect.Array, reflect.Map, reflect.String:
		if rv.Kind() == reflect.String {
			return "string"
		}
		return fmt.Sprintf("%s[%d]", rv.Type().String(), rv.Len())
	case reflect.Ptr:
		if rv.IsNil() {
			return rv.Type().String() + "(nil)"
		}
		return rv.Type().String()
	}
	return rv.Type().String()
}

func canonical(v any, depth int) (string, bool) {
	if v == nil {
		return "nil", true
	}
	rv := reflect.ValueOf(v)
	return canonicalValue(rv, depth)
}

func canonicalValue(rv reflect.Value, depth int) (string, bool) {
	switch rv.Kind() {
	case reflect.Bool, reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Float32, reflect.Float64:
		return fmt.Sprintf("%s:%v", rv.Kind(), rv.Interface()), true
	case reflect.String:
		return "string:" + strconv.Quote(rv.String()), true
	case reflect.Ptr, reflect.Interface:
		if rv.IsNil() {
			return "nil", true
		}
		if depth == 0 {
			return "", false
		}
		return canonicalValue(rv.Elem(), depth-1)
	case reflect.Slice, reflect.Array:
		if depth == 0 || rv.Len() > digestWidth {
			return "", false
		}
		parts := make([]string, 0, rv.Len())
		for i := 0; i < rv.Len(); i++ {
			c, ok := canonicalValue(rv.Index(i), depth-1)
			if !ok {
				return "", false
			}
			parts = append(parts, c)
		}
		return "array[" + strings.Join(parts, ",") + "]", true
	case reflect.Map:
		if depth == 0 || rv.Len() > digestWidth {
			return "", false
		}
		items := make([]string, 0, rv.Len())
		iter := rv.MapRange()
		for iter.Next() {
			k, ok1 := canonicalValue(iter.Key(), depth-1)
			val, ok2 := canonicalValue(iter.Value(), depth-1)
			if !ok1 || !ok2 {
				return "", false
			}
			items = append(items, k+"="+val)
		}
		sort.Strings(items)
		return "map{" + strings.Join(items, ",") + "}", true
	case reflect.Struct:
		if depth == 0 || rv.NumField() > digestWidth {
			return "", false
		}
		t := rv.Type()
		items := make([]string, 0, rv.NumField())
		for i := 0; i < rv.NumField(); i++ {
			f := t.Field(i)
			if !f.IsExported() {
				continue
			}
			c, ok := canonicalValue(rv.Field(i), depth-1)
			if !ok {
				return "", false
			}
			items = append(items, f.Name+"="+c)
		}
		return t.String() + "{" + strings.Join(items, ",") + "}", true
	}
	return "", false
}

func digest(v any) string {
	c, ok := canonical(v, digestDepth)
	if !ok {
		return ""
	}
	h := sha256.Sum256([]byte(c))
	return hex.EncodeToString(h[:])[:16]
}

func bucket(rv reflect.Value) (string, bool) {
	if !rv.IsValid() {
		return "none", true
	}
	switch rv.Kind() {
	case reflect.Bool:
		if rv.Bool() {
			return "bool:true", true
		}
		return "bool:false", true
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		v := rv.Int()
		if v == 0 {
			return "num:zero", true
		} else if v > 0 {
			return "num:pos", true
		}
		return "num:neg", true
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		if rv.Uint() == 0 {
			return "num:zero", true
		}
		return "num:pos", true
	case reflect.Float32, reflect.Float64:
		v := rv.Float()
		if v == 0 {
			return "num:zero", true
		} else if v > 0 {
			return "num:pos", true
		}
		return "num:neg", true
	case reflect.String:
		if rv.Len() == 0 {
			return "str:empty", true
		}
		return "str:nonempty", true
	case reflect.Slice, reflect.Map, reflect.Array:
		n := rv.Len()
		if n == 0 {
			return "coll:empty", true
		} else if n == 1 {
			return "coll:one", true
		}
		return "coll:many", true
	case reflect.Ptr, reflect.Interface:
		if rv.IsNil() {
			return "none", true
		}
		return "obj:" + rv.Elem().Type().String(), true
	case reflect.Struct:
		return "obj:" + rv.Type().String(), true
	case reflect.Func, reflect.Chan:
		return "", false
	}
	return "", false
}

func stateFacts(recv any) [][3]string {
	facts := [][3]string{}
	if recv == nil {
		return facts
	}
	rv := reflect.ValueOf(recv)
	for rv.Kind() == reflect.Ptr {
		if rv.IsNil() {
			return facts
		}
		rv = rv.Elem()
	}
	facts = append(facts, [3]string{"self:type", "obj:" + rv.Type().String(), digest(rv.Type().String())})
	if rv.Kind() != reflect.Struct {
		return facts
	}
	t := rv.Type()
	for i := 0; i < rv.NumField() && i < digestWidth; i++ {
		f := t.Field(i)
		b, ok := bucket(rv.Field(i))
		if !ok {
			continue
		}
		d := ""
		if strings.HasPrefix(b, "obj:") {
			d = digest(b[4:])
		}
		facts = append(facts, [3]string{"self." + f.Name, b, d})
	}
	return facts
}

func argShapes(names []string, values []any) [][3]string {
	out := [][3]string{}
	for i, v := range values {
		if i >= maxArgs {
			break
		}
		name := fmt.Sprintf("arg%d", i)
		if i < len(names) && names[i] != "" {
			name = names[i]
		}
		out = append(out, [3]string{name, shape(v), digest(v)})
	}
	return out
}

// ----------------------------------------------------------------------------- executions

func current() *execution {
	if len(active) == 0 {
		return nil
	}
	return active[len(active)-1]
}

func (e *execution) intern(id, origin, file string, line int) {
	if _, ok := e.symbols[id]; ok {
		return
	}
	var loc *location
	if file != "" {
		loc = &location{Path: file, Line: line}
	}
	e.symbols[id] = symbol{ID: id, Origin: origin, Location: loc}
}

func (e *execution) originOf(nodeID int) string {
	n := e.nodes[nodeID]
	if n.Type != "call" {
		return "unknown"
	}
	if s, ok := e.symbols[n.Symbol]; ok {
		return s.Origin
	}
	return "unknown"
}

func (e *execution) thread(gid int64) int {
	if t, ok := e.goroutine[gid]; ok {
		return t
	}
	t := len(e.goroutine)
	e.goroutine[gid] = t
	return t
}

// Begin marks the start of a stimulus (a test or subtest).
func Begin(ref string) {
	mu.Lock()
	defer mu.Unlock()
	e := &execution{ref: ref, symbols: map[string]symbol{}, stacks: map[int64][]int{}, goroutine: map[int64]int{}}
	sym := "go:" + ref
	e.intern(sym, "test", "", 0)
	e.nodes = append(e.nodes, &node{Type: "call", ID: 0, Parent: nil, Symbol: sym, Args: [][3]string{}, Outcome: "unknown"})
	e.thread(goid())
	active = append(active, e)
}

// End closes the innermost stimulus and writes its Execution.
func End(failed bool) {
	mu.Lock()
	defer mu.Unlock()
	e := current()
	if e == nil {
		return
	}
	active = active[:len(active)-1]
	if outDir == "" {
		return
	}
	outcome := "passed"
	if failed {
		outcome = "failed"
	}
	syms := make([]symbol, 0, len(e.symbols))
	for _, s := range e.symbols {
		syms = append(syms, s)
	}
	sort.Slice(syms, func(i, j int) bool { return syms[i].ID < syms[j].ID })
	revision := rev
	var revPtr *string
	if revision != "" {
		revPtr = &revision
	}
	idRev := revision
	if idRev == "" {
		idRev = "unknown"
	}
	doc := map[string]any{
		"id":           e.ref + "@" + idRev,
		"stimulus":     stim,
		"stimulus_ref": e.ref,
		"outcome":      outcome,
		"revision":     revPtr,
		"collectors": []map[string]string{
			{"name": "go-source-instrumentation", "plane": "symbol", "fidelity": "complete"},
		},
		"symbols":     syms,
		"nodes":       e.nodes,
		"branches":    append([]branchObs{}, e.branches...),
		"diagnostics": [][2]string{{"goroutines", strconv.Itoa(len(e.goroutine))}},
	}
	_ = os.MkdirAll(outDir, 0o755)
	h := sha256.Sum256([]byte(e.ref))
	name := strings.Map(func(r rune) rune {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '_' || r == '.' || r == '-' {
			return r
		}
		return '_'
	}, e.ref)
	if len(name) > 100 {
		name = name[:100]
	}
	data, _ := json.MarshalIndent(doc, "", " ")
	_ = os.WriteFile(filepath.Join(outDir, name+"-"+hex.EncodeToString(h[:])[:12]+".json"), append(data, '\n'), 0o644)
}

// ----------------------------------------------------------------------------- calls

// Enter records a call. Test doubles (test-origin functions entered from repo code) get a
// substitution wrapper carrying the static claim, so they are non-leaf stand-ins.
func Enter(m Meta, values ...any) *Ctx {
	mu.Lock()
	defer mu.Unlock()
	e := current()
	if e == nil {
		return nil
	}
	gid := goid()
	e.intern(m.Sym, m.Origin, m.File, m.Line)
	args := argShapes(m.Params, values)
	stack := e.stacks[gid]
	parent := 0
	if len(stack) > 0 {
		parent = stack[len(stack)-1]
	}
	sub := -1
	if m.Origin == "test" && e.originOf(parent) == "repo" {
		mech := "fake"
		if strings.Contains(m.Sym, "<anon>") || !strings.Contains(strings.TrimPrefix(m.Sym, "go:"), ".") {
			mech = "stub"
		}
		var claimed *string
		relation := "none"
		if m.Claim != "" {
			c := m.Claim
			claimed = &c
			relation = m.Relation
			e.intern(c, "repo", "", 0)
		}
		p := parent
		n := &node{Type: "substitution", ID: len(e.nodes), Parent: &p, Collector: 0, Mechanism: mech,
			Substitute: m.Sym, Claimed: claimed, Relation: relation, Path: []string{}, Args: args, Outcome: "unknown",
			State: [][3]string{}}
		e.nodes = append(e.nodes, n)
		sub = n.ID
		parent = sub
	}
	p := parent
	n := &node{Type: "call", ID: len(e.nodes), Parent: &p, Symbol: m.Sym, Collector: 0, Args: args,
		Thread: e.thread(gid), Outcome: "unknown", State: stateFacts(m.Recv)}
	e.nodes = append(e.nodes, n)
	e.stacks[gid] = append(stack, n.ID)
	return &Ctx{id: n.ID, sub: sub, gid: gid, exec: e, recv: m.Recv}
}

func settle(e *execution, id int, outcome, result string) {
	if id < 0 || id >= len(e.nodes) {
		return
	}
	n := e.nodes[id]
	if n.Outcome != "unknown" {
		return
	}
	n.Outcome = outcome
	n.Result = result
}

func (e *execution) pop(gid int64, id int) {
	stack := e.stacks[gid]
	for i := len(stack) - 1; i >= 0; i-- {
		if stack[i] == id {
			e.stacks[gid] = stack[:i]
			return
		}
	}
}

// Exit records a normal return. A trailing non-nil error result is the "raised" outcome
// in Go's convention; other results are digested.
func Exit(c *Ctx, results ...any) {
	if c == nil {
		return
	}
	mu.Lock()
	defer mu.Unlock()
	outcome := "returned"
	vals := results
	if n := len(results); n > 0 {
		if err, ok := results[n-1].(error); ok && err != nil {
			outcome = "returned-error:go:" + reflect.TypeOf(err).String()
			c.exec.intern("go:"+reflect.TypeOf(err).String(), "external", "", 0)
			vals = results[:n-1]
		} else if results[n-1] == nil {
			if _, isErrSlot := results[n-1].(error); !isErrSlot {
				vals = results
			}
		}
	}
	res := ""
	if outcome == "returned" {
		if len(vals) == 1 {
			res = digest(vals[0])
		} else if len(vals) > 1 {
			res = digest(vals)
		}
	}
	settle(c.exec, c.id, outcome, res)
	if c.sub >= 0 {
		settle(c.exec, c.sub, outcome, res)
	}
	c.exec.nodes[c.id].StateAfter = stateFacts(c.recv)
	c.exec.pop(c.gid, c.id)
}

// Branch records the outcome of the `if` condition at `site` (an id computed by the
// instrumenter from the condition's span in the ORIGINAL source) and returns it unchanged.
func Branch(site string, cond bool) bool {
	mu.Lock()
	defer mu.Unlock()
	e := current()
	if e == nil {
		return cond
	}
	stack := e.stacks[goid()]
	node := 0
	if len(stack) > 0 {
		node = stack[len(stack)-1]
	}
	e.branches = append(e.branches, branchObs{Site: site, Outcome: cond, Node: node, Seq: len(e.nodes)})
	return cond
}

// Panic records a panic unwinding through the call.
func Panic(c *Ctx, r any) {
	if c == nil {
		return
	}
	mu.Lock()
	defer mu.Unlock()
	t := "go:panic"
	if r != nil {
		t = "go:" + reflect.TypeOf(r).String()
	}
	c.exec.intern(t, "external", "", 0)
	settle(c.exec, c.id, "panic:"+t, "")
	if c.sub >= 0 {
		settle(c.exec, c.sub, "panic:"+t, "")
	}
	c.exec.nodes[c.id].StateAfter = stateFacts(c.recv)
	c.exec.pop(c.gid, c.id)
}
