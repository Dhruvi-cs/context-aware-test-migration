"""Generic kill-set runner: for ANY test command that prints 'PASS name'/'FAIL name' lines and reads BASE_URL,
computes K(T) per test over the same deterministic mutant list as runner.py.
  python mutation/killset_runner.py --label selenium_src --cmd "python tests_src/source_selenium.py" --workers 2
Output: results/killset_<label>.json   (use --limit N for a smoke run; --env KEY=VAL to pass extra env)"""
import argparse, ast, json, os, shlex, shutil, socket, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import enumerate_server, apply_server, enumerate_client, apply_client

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUT = os.path.join(ROOT, "sut", "todo_app")


UNSAFE_PORTS = {5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697}

def free_port():
    for _ in range(50):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            if port not in UNSAFE_PORTS and port > 1024:
                return port
    return 8092


def parse(stdout):
    res = {}
    for line in stdout.splitlines():
        p = line.split()
        if len(p) >= 2 and p[0] in ("PASS", "FAIL"):
            res[p[1]] = p[0] == "PASS"
    return res


def run_variant(app_src, js_src, cmd, extra_env, timeout):
    tmp = tempfile.mkdtemp(prefix="mut_")
    os.makedirs(os.path.join(tmp, "static"))
    open(os.path.join(tmp, "app.py"), "w").write(app_src)
    open(os.path.join(tmp, "static", "app.js"), "w").write(js_src)
    port = free_port()
    p = subprocess.Popen([sys.executable, "app.py"], cwd=tmp, env=dict(os.environ, PORT=str(port)),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                if urlopen(base + "/health", timeout=1).read().decode() == "ok":
                    break
            except Exception:
                time.sleep(0.1)
        else:
            return {"valid": False, "reason": "startup/health failed"}
        try:
            r = subprocess.run(shlex.split(cmd), cwd=ROOT, env=dict(os.environ, BASE_URL=base, **extra_env),
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"valid": False, "reason": "test command timeout"}
        res = parse(r.stdout)
        if not res:
            return {"valid": False, "reason": "no PASS/FAIL output: " + (r.stderr or r.stdout)[-300:]}
        return {"valid": True, "results": res}
    finally:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--baseline-runs", type=int, default=3, help="all must be identical and fully green (flake check)")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--env", nargs="*", default=[])
    a = ap.parse_args()
    extra = dict(kv.split("=", 1) for kv in a.env)

    app_src = open(os.path.join(SUT, "app.py")).read()
    js_src = open(os.path.join(SUT, "static", "app.js")).read()
    base_app = ast.unparse(ast.parse(app_src))

    runs = [run_variant(base_app, js_src, a.cmd, extra, a.timeout) for _ in range(a.baseline_runs)]
    for i, r in enumerate(runs):
        assert r["valid"], f"baseline run {i} invalid: {r}"
    names = sorted(runs[0]["results"])
    unstable = sorted({n for r in runs for n in r["results"] if not all(x["results"].get(n) for x in runs)})
    passes_original = {n: all(x["results"].get(n, False) for x in runs) for n in names}
    print("baseline:", {n: ("PASS" if ok else "FAIL/FLAKY") for n, ok in passes_original.items() if not ok} or "all green", flush=True)

    jobs = []
    for s in enumerate_server(app_src):
        try: jobs.append((s, apply_server(app_src, s), js_src))
        except SyntaxError: jobs.append((s, None, None))
    for s in enumerate_client(js_src):
        jobs.append((s, base_app, apply_client(js_src, s)))
    if a.limit:
        jobs = jobs[:a.limit]

    def work(j):
        s, app, js = j
        if app is None:
            return {**s, "valid": False, "reason": "syntax"}
        r = run_variant(app, js, a.cmd, extra, a.timeout)
        if not r["valid"]:
            return {**s, **r}
        failed = sorted(t for t, ok in r["results"].items() if not ok)
        missing = sorted(set(names) - set(r["results"]))   # test did not report at all (crash) counts as failed
        return {**s, "valid": True, "failed": failed + missing}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(work, jobs))
    # K(T) = mutants on which T fails, counted only if T passes on the original app
    kill = {n: sorted(r["id"] for r in rows if r.get("valid") and n in r["failed"]) if passes_original[n] else []
            for n in names}
    out = {"label": a.label, "cmd": a.cmd, "tests": names, "passes_original": passes_original,
           "kill_sets": kill, "mutants": [{k: v for k, v in r.items() if k not in ("pattern", "repl")} for r in rows]}
    path = os.path.join(ROOT, "results", f"killset_{a.label}.json")
    json.dump(out, open(path, "w"), indent=1)
    valid = [r for r in rows if r.get("valid")]
    killed = {m for ks in kill.values() for m in ks}
    print(f"valid mutants {len(valid)}/{len(rows)}; killed by suite {len(killed & {r['id'] for r in valid})}; wrote {path}")


if __name__ == "__main__":
    main()
