"""Builds the kill matrix: for each mutant, start the mutated SUT and run the reference tests."""
import ast, json, os, shutil, socket, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
import requests
from engine import enumerate_server, apply_server, enumerate_client, apply_client

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUT = os.path.join(ROOT, "sut", "todo_app")
TESTS = os.path.join(SUT, "reference_http_tests.py")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def run_variant(app_src, js_src):
    tmp = tempfile.mkdtemp(prefix="mut_")
    os.makedirs(os.path.join(tmp, "static"))
    open(os.path.join(tmp, "app.py"), "w").write(app_src)
    open(os.path.join(tmp, "static", "app.js"), "w").write(js_src)
    port = free_port()
    p = subprocess.Popen([sys.executable, "app.py"], cwd=tmp, env=dict(os.environ, PORT=str(port)),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if requests.get(base + "/health", timeout=1).text == "ok":
                    break
            except Exception:
                time.sleep(0.1)
        else:
            return {"valid": False, "reason": "startup/health failed"}
        r = subprocess.run([sys.executable, TESTS], env=dict(os.environ, BASE_URL=base),
                           capture_output=True, text=True, timeout=120)
        res = {}
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("PASS", "FAIL"):
                res[parts[1]] = parts[0] == "PASS"
        return {"valid": True, "results": res}
    finally:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()
        shutil.rmtree(tmp, ignore_errors=True)


def main(workers=4):
    app_src = open(os.path.join(SUT, "app.py")).read()
    js_src = open(os.path.join(SUT, "static", "app.js")).read()
    base_app = ast.unparse(ast.parse(app_src))  # round-tripped baseline must be fully green
    baseline = run_variant(base_app, js_src)
    assert baseline["valid"] and baseline["results"] and all(baseline["results"].values()), f"baseline not green: {baseline}"
    jobs = []
    for s in enumerate_server(app_src):
        try:
            jobs.append((s, apply_server(app_src, s), js_src))
        except SyntaxError:
            jobs.append((s, None, None))
    for s in enumerate_client(js_src):
        jobs.append((s, base_app, apply_client(js_src, s)))

    def work(j):
        s, a, j_ = j
        if a is None:
            return {**s, "valid": False, "reason": "syntax"}
        r = run_variant(a, j_)
        if not r["valid"]:
            return {**s, **r}
        killed = sorted(t for t, ok in r["results"].items() if not ok)
        return {**s, "valid": True, "killed_by": killed, "killed": bool(killed)}

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(work, jobs))
    out = {"tests": sorted(baseline["results"]), "baseline_green": True, "mutants": rows}
    json.dump(out, open(os.path.join(ROOT, "results", "kill_matrix.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    t = time.time(); o = main()
    for tgt in ("server", "client"):
        rows = [m for m in o["mutants"] if m["target"] == tgt]
        valid = [m for m in rows if m["valid"]]
        killed = [m for m in valid if m["killed"]]
        print(f"{tgt}: generated={len(rows)} valid={len(valid)} killed_by_http_tests={len(killed)} "
              f"survived={len(valid) - len(killed)} invalid={len(rows) - len(valid)}")
    print(f"elapsed {time.time() - t:.0f}s")
