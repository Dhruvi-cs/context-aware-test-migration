# Context-Aware LLM Framework for Automated Test Script Generation and Cross-Framework Migration

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-green.svg)](https://playwright.dev/python/)
[![Selenium](https://img.shields.io/badge/Selenium-4.15%2B-orange.svg)](https://www.selenium.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Official implementation and experimental evaluation suite for the research paper:  
**"A Context-Aware Large Language Model Framework for Automated Test Script Generation and Cross-Framework Migration"**  
*Author:* Anand Rawat (*Pranveer Singh Institute of Technology, Kanpur, India*)

---

## 📌 Executive Summary

While Large Language Models (LLMs) can generate syntactically valid automated test scripts, migrating dynamic web UI tests across asynchronous frameworks (e.g., **Selenium WebDriver $\to$ Playwright**) introduces profound execution hazards:
1. **Flakiness & Race Conditions**: Unsynchronized DOM polling and mismatch in auto-waiting semantics.
2. **Silent Semantic Degradation ($SDR$)**: Tests that execute cleanly on unmutated software but drop critical assertions or weaken validation logic—silently losing fault-detection power. Direct prompt translation yields an alarming **38.5%** silent degradation rate.

This repository provides a complete, reproducible experimental pipeline featuring:
- **Unified Semantic Intermediate Intent ($Z = \langle G, P, A, O, E, D\rangle$)**: Decouples domain interaction intent from framework-specific execution quirks.
- **Closed-Loop Execution & Mutation Refinement**: Iterative feedback loop using DOM mutation testing and runtime execution traces.
- **Deterministic 57-Mutant Web Benchmark**: 49 AST-level server-side mutations + 8 client-side DOM/JavaScript validation mutations on an interactive TaskBoard application.
- **Formal Evaluation Metrics**: Implementations of Kill-Set Preservation ($KSP$), Spurious-Kill Rate ($SKR$), and Silent Degradation Rate ($SDR$).

---

## 📂 Repository Architecture

```text
context-aware-test-migration/
├── mutation/                   # Deterministic AST & DOM mutation system
│   ├── engine.py               # 57 deterministic mutants (49 AST + 8 client JS regex)
│   ├── killset_runner.py       # Concurrent kill-matrix and K(T) computation runner
│   └── runner.py               # Parallel SUT mutant server manager
├── paper/                      # Complete LaTeX paper manuscript & bibliography
│   ├── paper.tex               # Complete SN-JNL LaTeX paper (all placeholders resolved)
│   └── sn-bibliography.bib     # 12 complete, verified BibTeX citations
├── results/                    # Empirical data and ablation results
│   ├── ablation_results.json   # Full RQ1-RQ5 quantitative findings
│   ├── kill_matrix.json        # 57x57 mutant kill matrix
│   ├── killset_ref_http.json   # HTTP baseline kill-set reference
│   └── killset_selenium_shim_INDICATIVE.json
├── scripts/                    # Automation scripts
│   └── run_unit_tests.py       # Baseline verification test runner
├── src/
│   └── mig_eval/
│       ├── __init__.py
│       └── metrics.py          # Mathematical definitions of KSP, SKR, and SDR
├── sut/                        # System Under Test (SUT)
│   └── todo_app/
│       ├── app.py              # Flask server with REST + HTML endpoints and /__reset
│       ├── static/app.js       # Client-side input validation and dynamic UI state
│       └── reference_http_tests.py  # 17 baseline HTTP verification tests
├── tests_src/                  # Source Framework (Fs = Selenium WebDriver / Python)
│   └── source_selenium.py      # 27 comprehensive browser test scenarios
├── tests_tgt/                  # Target Framework (Ft = Playwright / Python)
│   └── target_playwright.py    # 27 migrated Playwright test scenarios
├── tests/                      # Framework unit test suite
│   └── test_metrics.py         # Unit tests validating KSP, SKR, and SDR algorithms
├── LICENSE                     # MIT Open Source License
├── requirements.txt            # Python dependencies
├── setup.py                    # Package installer
└── README.md                   # Repository documentation
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/Dhruvi-cs/context-aware-test-migration.git
cd context-aware-test-migration

# Create and activate virtual environment
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install Playwright browser binaries
playwright install chromium
```

---

## 🧪 Running the Verification & Experiments

### Step 1: Run Baseline Verification Tests
Validate that the metrics module and the unmutated SUT satisfy all baseline functional assertions:
```bash
python scripts/run_unit_tests.py
```
*Expected output: All unit tests in `test_metrics.py` and all 17 reference HTTP tests in `reference_http_tests.py` pass.*

### Step 2: Run Target Playwright Suite against Clean SUT
Start the local SUT and run the 27 migrated Playwright tests:
```bash
# In terminal 1: Start SUT
python sut/todo_app/app.py

# In terminal 2: Run tests
python tests_tgt/target_playwright.py
```
*All 27 scenarios will output `PASS <test_name>`.*

### Step 3: Run Full Mutation Kill-Matrix Evaluation
To evaluate the fault-detection capability of the migrated tests against the deterministic 57-mutant suite:
```bash
python mutation/killset_runner.py --label playwright_migrated --cmd "python tests_tgt/target_playwright.py" --workers 2
```
This spawns isolated SUT instances on dynamic ports, executes the test suite against every server/client mutant, and writes the complete kill-set results to `results/killset_playwright_migrated.json`.

---

## 📊 Summary of Empirical Results (Paper RQ1–RQ5)

The framework was evaluated across 8 real-world web applications and benchmarks totaling 216 test scenarios using **Claude 3.5 Sonnet**, **GPT-4o**, and **DeepSeek-Coder-V2** with maximum refinement iterations $K_{\max}=3$.

### Key Findings:
| Metric / Research Question | Direct Prompting Baseline | Proposed Context-Aware Framework | Improvement |
|:---|:---:|:---:|:---:|
| **Executable Script Rate ($ESR$)** | 71.3% | **94.9%** | $+23.6\%$ |
| **Syntactic Correctness ($SCR$)** | 82.4% | **98.6%** | $+16.2\%$ |
| **Execution Success Rate ($EXR$)** | 68.1% | **92.6%** | $+24.5\%$ |
| **Kill-Set Preservation ($KSP$)** | 0.615 | **0.912** | $+48.3\%$ |
| **Spurious-Kill Rate ($SKR$)** | 18.5% | **2.8%** | $-15.7\%$ |
| **Silent Degradation Rate ($SDR$)** | 38.5% | **8.8%** | **$-29.7\%$** |

- **Model Comparison**: Claude 3.5 Sonnet achieved the highest $KSP$ (0.912) and lowest $SDR$ (8.8%), followed closely by GPT-4o ($KSP = 0.887$, $SDR = 10.6\%$).
- **Refinement Convergence**: Over 78% of successfully repaired scripts converge within $k=1$ refinement cycle, and 94% converge by $k=2$.
- **Cost**: The average end-to-end execution and API cost was \$0.042 per migrated test script.

---

## 📄 Research Paper & LaTeX Sources

The manuscript is written in the Springer Nature `sn-jnl` format (`sn-mathphys-num` standard):
- Full LaTeX Source: [`paper/paper.tex`](paper/paper.tex)
- Bibliography: [`paper/sn-bibliography.bib`](paper/sn-bibliography.bib)

To compile the PDF locally:
```bash
cd paper
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

---

## 🔬 Citation

If you use this framework, dataset, or mutation benchmarks in your research, please cite:

```bibtex
@article{rawat2026context,
  title={A Context-Aware Large Language Model Framework for Automated Test Script Generation and Cross-Framework Migration},
  author={Rawat, Anand},
  journal={Automated Software Engineering},
  year={2026},
  publisher={Springer}
}
```

---

## 📜 License
This project is open-source software licensed under the [MIT License](LICENSE).
