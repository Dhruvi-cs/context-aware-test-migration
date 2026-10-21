(function () {
  var MAX = 100;
  var input = document.getElementById("task-input");
  var btn = document.getElementById("add-btn");
  var counter = document.getElementById("char-count");
  if (!input) { return; }
  function refresh() {
    var len = input.value.trim().length;
    btn.disabled = len === 0 || len > MAX;
    counter.textContent = String(MAX - input.value.length);
  }
  input.addEventListener("input", refresh);
  refresh();
})();
