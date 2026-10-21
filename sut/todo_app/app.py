"""TaskBoard - small Flask web app used as the system under test (SUT)."""
import os
import threading

from flask import (Flask, flash, get_flashed_messages, jsonify, redirect,
                   render_template_string, request, session)

MAX_TITLE = 100
USERNAME = "demo"
PASSWORD = "demo123"

app = Flask(__name__)
app.secret_key = "sut-not-a-secret"
_lock = threading.Lock()
STATE = {"tasks": [], "next_id": 1}
TRACE = []
TRACE_ON = os.environ.get("SUT_TRACE", "0") == "1"

LOGIN_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>TaskBoard - Login</title></head>
<body>
<h1>Sign in</h1>
{% if error %}<div id="login-error" class="error">{{ error }}</div>{% endif %}
<form id="login-form" method="post" action="/login">
  <label for="username">Username</label>
  <input id="username" name="username" type="text">
  <label for="password">Password</label>
  <input id="password" name="password" type="password">
  <button id="login-btn" type="submit">Log in</button>
</form>
</body></html>"""

MAIN_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>TaskBoard</title></head>
<body>
<h1>TaskBoard</h1>
<a id="logout" href="/logout">Log out</a>
{% for m in messages %}<div id="flash" class="flash">{{ m }}</div>{% endfor %}
<form id="add-form" method="post" action="/add">
  <input id="task-input" name="title" type="text" placeholder="What needs doing?">
  <span id="char-count">100</span>
  <button id="add-btn" type="submit">Add</button>
</form>
<nav>
  <a id="filter-all" href="/?filter=all">All</a>
  <a id="filter-active" href="/?filter=active">Active</a>
  <a id="filter-done" href="/?filter=done">Done</a>
</nav>
<ul id="task-list">
{% for t in tasks %}
  <li id="task-{{ t.id }}" class="task{% if t.done %} done{% endif %}">
    <span class="task-title">{{ t.title }}</span>
    <form method="post" action="/toggle/{{ t.id }}"><button class="toggle-btn" type="submit">Toggle</button></form>
    <form method="post" action="/delete/{{ t.id }}"><button class="delete-btn" type="submit">Delete</button></form>
  </li>
{% endfor %}
</ul>
<p><span id="remaining">{{ remaining }}</span> items left</p>
<form method="post" action="/clear-completed"><button id="clear-completed" type="submit">Clear completed</button></form>
<script src="/static/app.js"></script>
</body></html>"""


@app.before_request
def _trace():
    if TRACE_ON and not request.path.startswith(("/__", "/static")):
        keys = ",".join(sorted(request.form.keys()))
        TRACE.append(f"{request.method} {request.path} [{keys}]")


def _logged_in():
    return session.get("user") == USERNAME


@app.route("/health")
def health():
    return "ok"


@app.route("/__reset", methods=["POST"])
def reset():
    with _lock:
        STATE["tasks"] = []
        STATE["next_id"] = 1
        TRACE.clear()
    return "reset"


@app.route("/__trace")
def trace():
    return jsonify(TRACE)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")
        if user == USERNAME and pw == PASSWORD:
            session["user"] = user
            return redirect("/")
        error = "Invalid credentials"
    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


@app.route("/")
def index():
    if not _logged_in():
        return redirect("/login")
    flt = request.args.get("filter", "all")
    with _lock:
        tasks = list(STATE["tasks"])
    remaining = len([t for t in tasks if not t["done"]])
    if flt == "active":
        tasks = [t for t in tasks if not t["done"]]
    elif flt == "done":
        tasks = [t for t in tasks if t["done"]]
    return render_template_string(MAIN_TEMPLATE, tasks=tasks, remaining=remaining,
                                  messages=get_flashed_messages())


@app.route("/add", methods=["POST"])
def add():
    if not _logged_in():
        return redirect("/login")
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required")
    elif len(title) > MAX_TITLE:
        flash("Title too long")
    else:
        with _lock:
            STATE["tasks"].append({"id": STATE["next_id"], "title": title, "done": False})
            STATE["next_id"] += 1
    return redirect("/")


@app.route("/toggle/<int:tid>", methods=["POST"])
def toggle(tid):
    if not _logged_in():
        return redirect("/login")
    with _lock:
        for t in STATE["tasks"]:
            if t["id"] == tid:
                t["done"] = not t["done"]
    return redirect("/")


@app.route("/delete/<int:tid>", methods=["POST"])
def delete(tid):
    if not _logged_in():
        return redirect("/login")
    with _lock:
        STATE["tasks"] = [t for t in STATE["tasks"] if t["id"] != tid]
    return redirect("/")


@app.route("/clear-completed", methods=["POST"])
def clear_completed():
    if not _logged_in():
        return redirect("/login")
    with _lock:
        STATE["tasks"] = [t for t in STATE["tasks"] if not t["done"]]
    return redirect("/")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), threaded=True)
