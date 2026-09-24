import itertools, json, math, os, subprocess, sys, tempfile, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flakelens import Case, run_case, run_suite, wilson, runs_needed, to_markdown, to_json

# --- statistics -------------------------------------------------------------
def test_wilson_all_pass_is_not_a_point():
    lo, hi = wilson(10, 10)
    assert hi == 1.0
    assert 0.6 < lo < 1.0          # must NOT collapse to 1.0

def test_wilson_all_fail_upper_bound_below_one():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and 0.0 < hi < 0.4

def test_wilson_widens_with_less_data():
    n_lo, _ = wilson(3, 3)
    m_lo, _ = wilson(30, 30)
    assert m_lo > n_lo             # more evidence -> tighter bound

def test_wilson_zero_runs_is_maximally_uncertain():
    assert wilson(0, 0) == (0.0, 1.0)

def test_runs_needed_is_sane():
    n = runs_needed(0.95)
    assert 50 < n < 200 and wilson(n, n)[0] >= 0.95

# --- classification ---------------------------------------------------------
def test_stable_pass():
    r = run_case(lambda p: '{"a":1}', Case("c","p",{"is_json":True}), n=5)
    assert r.status == "PASS" and r.passes == 5

def test_broken():
    r = run_case(lambda p: "nope", Case("c","p",{"is_json":True}), n=5)
    assert r.status == "FAIL" and r.failed_checks["is_json"] == 5

def test_flaky_detected_and_bounded():
    flip = itertools.cycle(['{"a":1}', "nope"])
    r = run_case(lambda p: next(flip), Case("c","p",{"is_json":True}), n=10)
    assert r.status == "FLAKY" and r.passes == 5
    lo, hi = r.ci
    assert lo < 0.5 < hi           # interval brackets the true rate

def test_distinct_outputs_counted():
    seq = itertools.cycle(["a","b","a"])
    r = run_case(lambda p: next(seq), Case("c","p",{"contains":"a"}), n=6)
    assert r.distinct_outputs == 2

def test_exception_counts_as_failure():
    def boom(p): raise RuntimeError("upstream 503")
    r = run_case(boom, Case("c","p",{"is_json":True}), n=3)
    assert r.status == "FAIL" and "503" in r.errors[0] and len(r.latencies_ms) == 3

def test_unknown_check_raises():
    with pytest.raises(ValueError, match="unknown check"):
        run_case(lambda p: "x", Case("c","p",{"bogus":1}), n=1)

# --- checks -----------------------------------------------------------------
@pytest.mark.parametrize("checks,out,ok", [
    ({"contains": ["a","b"]}, "a and b", True),
    ({"contains": ["a","z"]}, "a and b", False),
    ({"not_contains": "ssn"}, "no id here", True),
    ({"regex": r"^\d{3}$"}, "123", True),
    ({"is_json": ["k"]}, '{"k":1}', True),
    ({"is_json": ["k"]}, '{"j":1}', False),
    ({"max_chars": 3}, "abcd", False),
    ({"min_chars": 2}, "ab", True),
    ({"equals": "hi"}, "  hi  ", True),
])
def test_check_matrix(checks, out, ok):
    r = run_case(lambda p: out, Case("c","p",checks), n=1)
    assert (r.status == "PASS") is ok

# --- reporting --------------------------------------------------------------
def test_markdown_separates_broken_from_flaky():
    flip = itertools.cycle(["ok","no"])
    rs = [run_case(lambda p:"ok",  Case("good","p",{"contains":"ok"}), n=4),
          run_case(lambda p:"no",  Case("bad","p",{"contains":"ok"}), n=4),
          run_case(lambda p:next(flip), Case("flk","p",{"contains":"ok"}), n=4)]
    md = to_markdown(rs, 4)
    assert "Broken" in md and "`bad`" in md
    assert "Flaky" in md and "`flk`" in md
    assert "1 stable, 1 broken, 1 flaky" in md
    assert md.index("Broken") < md.index("Flaky")     # worst first

def test_json_roundtrips():
    rs = [run_case(lambda p:"ok", Case("g","p",{"contains":"ok"}), n=3)]
    d = json.loads(to_json(rs, 3))
    assert d["summary"]["stable"] == 1
    assert d["cases"][0]["ci95"][0] > 0 and d["cases"][0]["rate"] == 1.0

# --- CLI --------------------------------------------------------------------
def test_cli_end_to_end_exit_codes(tmp_path):
    prov = tmp_path/"prov.py"
    prov.write_text("def call(p):\n    return 'nope' if 'bad' in p else '{\"a\":1}'\n")
    cases = tmp_path/"c.json"
    cases.write_text(json.dumps([
        {"id":"good","prompt":"good","checks":{"is_json":True}},
        {"id":"bad","prompt":"bad","checks":{"is_json":True}}]))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, PYTHONPATH=root)
    r = subprocess.run([sys.executable,"-m","flakelens.cli",str(cases),
                        "--provider","prov:call","--runs","3",
                        "--out",str(tmp_path/"r.md")],
                       cwd=tmp_path, capture_output=True, text=True, env=env)
    assert r.returncode == 1, r.stderr          # broken case -> exit 1
    assert "Broken" in (tmp_path/"r.md").read_text()

def test_cli_rejects_one_run(tmp_path):
    cases = tmp_path/"c.json"; cases.write_text("[]")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable,"-m","flakelens.cli",str(cases),
                        "--provider","x:y","--runs","1"],
                       cwd=tmp_path, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=root))
    assert r.returncode != 0 and "runs must be >= 2" in r.stderr
