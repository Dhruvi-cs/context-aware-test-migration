"""AST and Rule-Based Classical Transpiler for Selenium -> Playwright Migration.
Implements syntax-directed AST and pattern rewriting rules without LLM intervention.
Used as the classical baseline (Baseline-0) to test whether LLM reasoning is strictly necessary.
"""
import ast
import os
import re
import sys

class SeleniumASTTransformer(ast.NodeTransformer):
    """AST Transformer that converts common Selenium patterns to Playwright syntax."""

    def visit_Call(self, node):
        self.generic_visit(node)
        
        # Transform click_and_wait_nav(arg) -> arg.click()
        if isinstance(node.func, ast.Name) and node.func.id == "click_and_wait_nav" and len(node.args) == 1:
            target = node.args[0]
            return ast.Call(
                func=ast.Attribute(value=target, attr="click", ctx=ast.Load()),
                args=[],
                keywords=[]
            )

        # Transform driver().find_element(By.ID, "foo") -> driver().locator("#foo")
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("find_element", "find_elements"):
                if len(node.args) >= 2:
                    by_arg = node.args[0]
                    sel_arg = node.args[1]
                    node.func.attr = "locator"
                    if isinstance(by_arg, ast.Attribute) and by_arg.attr == "ID" and isinstance(sel_arg, ast.Constant):
                        node.args = [ast.Constant(value=f"#{sel_arg.value}")]
                    else:
                        node.args = [sel_arg]
            elif attr == "send_keys":
                node.func.attr = "fill"
            elif attr == "get" and isinstance(node.func.value, (ast.Name, ast.Call)):
                # Only transform d.get() or driver().get(), not os.environ.get() or dict.get()
                val = node.func.value
                val_name = val.id if isinstance(val, ast.Name) else (val.func.id if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) else "")
                if val_name in ("d", "driver", "page", "get_page"):
                    node.func.attr = "goto"
            elif attr == "delete_all_cookies":
                # driver().delete_all_cookies() -> _context.clear_cookies()
                return ast.Call(
                    func=ast.Attribute(value=ast.Name(id="_context", ctx=ast.Load()), attr="clear_cookies", ctx=ast.Load()),
                    args=[],
                    keywords=[]
                )
            elif attr == "quit":
                node.func.attr = "close"

        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr == "current_url":
            node.attr = "url"
        return node

def transpile(source_code: str) -> str:
    # First, strip Selenium-specific imports and helper functions that don't exist in Playwright
    lines = source_code.splitlines()
    filtered = []
    skip = False
    for line in lines:
        if line.startswith("from selenium") or "import WebDriverWait" in line:
            continue
        if line.startswith("def driver():") or line.startswith("def wait():") or line.startswith("def click_and_wait_nav"):
            skip = True
            continue
        if skip:
            if line.startswith("def ") or (line and not line.startswith(" ") and not line.startswith("\t")):
                skip = False
            else:
                continue
        filtered.append(line)

    code = "\n".join(filtered)
    
    # Prepend Playwright boilerplate
    header = '''"""Rule-Based Transpiled Playwright Test Suite (Baseline-0)"""
import argparse, os, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
_pw = None; _browser = None; _context = None; _page = None

def get_page():
    global _pw, _browser, _context, _page
    if _pw is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=os.environ.get("HEADLESS", "1") != "0")
        _context = _browser.new_context()
        _page = _context.new_page()
        _page.set_default_timeout(2500)
    return _page

def driver():
    return get_page()

'''
    # Parse into AST
    tree = ast.parse(code)
    transformer = SeleniumASTTransformer()
    transformed_tree = transformer.visit(tree)
    ast.fix_missing_locations(transformed_tree)
    
    body = ast.unparse(transformed_tree)
    # Post-process properties that are properties in Selenium but methods in Playwright
    # e.g. .text in Selenium is .inner_text() in Playwright
    body = re.sub(r'(\w+)\.text\b', r'\1.inner_text()', body)
    
    return header + body

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_file = os.path.join(root, "tests_src", "source_selenium.py")
    out_file = os.path.join(root, "tests_tgt", "target_rule_based.py")
    
    src = open(src_file, "r").read()
    res = transpile(src)
    with open(out_file, "w") as f:
        f.write(res)
    print(f"Transpiled successfully to {out_file}")

if __name__ == "__main__":
    main()
