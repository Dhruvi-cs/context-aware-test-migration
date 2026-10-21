"""Deterministic AST mutation engine for the server code, plus regex mutants for client JS.
A mutant is addressed by (op, node index in ast.walk order, sub-index) so it is reproducible."""
import ast, json, re, sys

CMP_SWAP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt,
            ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In,
            ast.Is: ast.IsNot, ast.IsNot: ast.Is}


def _decorator_ids(nodes):
    skip = set()
    for n in nodes:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                skip.update(id(x) for x in ast.walk(d))
    return skip


def enumerate_server(src):
    tree = ast.parse(src)
    nodes = list(ast.walk(tree))
    skip = _decorator_ids(nodes)
    top_str = {id(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
               and len(n.value.value) <= 30}
    cmp_str = {id(c) for n in nodes if isinstance(n, ast.Compare) for c in n.comparators
               if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    for n in tree.body:  # exclude the __main__ guard
        if isinstance(n, ast.If) and "__name__" in ast.unparse(n.test):
            skip.update(id(x) for x in ast.walk(n))
    # Instrumentation and reset-overwritten state are not product behaviour: never mutate them.
    for n in nodes:
        if isinstance(n, ast.FunctionDef) and n.name in {"_trace", "trace"}:
            skip.update(id(x) for x in ast.walk(n))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            t = n.targets[0]
            if (isinstance(t, ast.Name) and t.id in {"TRACE_ON", "TRACE", "STATE"}) or (
                    isinstance(t, ast.Attribute) and t.attr == "secret_key"):
                skip.update(id(x) for x in ast.walk(n))
    sites = []
    for i, n in enumerate(nodes):
        if id(n) in skip:
            continue
        ln = getattr(n, "lineno", 0)
        if isinstance(n, ast.Compare):
            for j, op in enumerate(n.ops):
                if type(op) in CMP_SWAP:
                    sites.append(dict(op="ROR", idx=i, sub=j, line=ln,
                                      desc=f"{type(op).__name__}->{CMP_SWAP[type(op)].__name__}"))
        elif isinstance(n, ast.BoolOp):
            sites.append(dict(op="LCR", idx=i, sub=0, line=ln, desc=f"{type(n.op).__name__} swapped"))
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            sites.append(dict(op="NOT", idx=i, sub=0, line=ln, desc="remove not"))
        elif isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            sites.append(dict(op="CNUM", idx=i, sub=0, line=ln, desc=f"{n.value}->{n.value + 1}"))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and (id(n) in top_str or id(n) in cmp_str):
            sites.append(dict(op="CSTR", idx=i, sub=0, line=ln, desc=f"{n.value!r}->{n.value + 'x'!r}"))
        if isinstance(n, (ast.FunctionDef, ast.If, ast.For, ast.With)):
            for fld in ("body", "orelse"):
                for pos, st in enumerate(getattr(n, fld, [])):
                    if isinstance(st, (ast.Assign, ast.AugAssign)) or (
                            isinstance(st, ast.Expr) and not isinstance(st.value, ast.Constant)) \
                            and not ast.unparse(st).startswith("TRACE."):
                        sites.append(dict(op="SDL", idx=i, sub=pos, field=fld, line=st.lineno,
                                          desc=f"delete: {ast.unparse(st)[:50]}"))
    for k, s in enumerate(sites):
        s["id"] = f"S{k:03d}"
        s["target"] = "server"
    return sites


def apply_server(src, site):
    tree = ast.parse(src)
    nodes = list(ast.walk(tree))
    n = nodes[site["idx"]]
    op = site["op"]
    if op == "ROR":
        n.ops[site["sub"]] = CMP_SWAP[type(n.ops[site["sub"]])]()
    elif op == "LCR":
        n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
    elif op == "NOT":
        for p in nodes:
            for f, v in ast.iter_fields(p):
                if v is n:
                    setattr(p, f, n.operand)
                elif isinstance(v, list):
                    for k, x in enumerate(v):
                        if x is n:
                            v[k] = n.operand
    elif op == "CNUM":
        n.value += 1
    elif op == "CSTR":
        n.value += "x"
    elif op == "SDL":
        getattr(n, site["field"])[site["sub"]] = ast.Pass()
    ast.fix_missing_locations(tree)
    out = ast.unparse(tree)
    compile(out, "<mutant>", "exec")
    return out


JS_RULES = [
    ("JS-CNUM", r"var MAX = 100;", "var MAX = 101;"),
    ("JS-ROR1", r"len === 0", "len !== 0"),
    ("JS-ROR2", r"len > MAX", "len >= MAX"),
    ("JS-LCR", r"len === 0 \|\| len > MAX", "len === 0 && len > MAX"),
    ("JS-ARITH", r"MAX - input\.value\.length", "MAX + input.value.length"),
    ("JS-TRIM", r"input\.value\.trim\(\)\.length", "input.value.length"),
    ("JS-DISABLE", r"btn\.disabled = ", "btn.disabled = false && "),
    ("JS-EVENT", r'addEventListener\("input"', 'addEventListener("change"'),
]


def enumerate_client(js):
    out = []
    for k, (op, pat, rep) in enumerate(JS_RULES):
        if re.search(pat, js):
            out.append(dict(id=f"C{k:03d}", op=op, pattern=pat, repl=rep, line=0,
                            desc=f"{pat} -> {rep}", target="client"))
    return out


def apply_client(js, site):
    return re.sub(site["pattern"], site["repl"], js, count=1)
