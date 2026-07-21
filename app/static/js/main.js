/* Janata Ki Baat — vanilla JS. No frameworks, no trackers. */
(function () {
  "use strict";

  /* ---------- write page: live letter preview ---------- */
  var tplData = document.getElementById("tpl-data");
  var preview = document.getElementById("letter-preview");
  if (tplData && preview) {
    var templates = JSON.parse(tplData.textContent);

    var q = function (sel) { return preview.querySelector(sel); };
    var esc = function (s) {
      var d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    };

    var nameInput = document.getElementById("f-name");
    var cityInput = document.getElementById("f-city");
    var paraInput = document.getElementById("f-para");

    function currentTemplate() {
      var checked = document.querySelector('input[name="template"]:checked');
      return checked ? templates[checked.value] : null;
    }

    function render() {
      var tpl = currentTemplate();
      var name = (nameInput.value || "").trim() || "Your Name";
      var city = (cityInput.value || "").trim() || "Your City";
      q('[data-lp="name"]').textContent = name;
      q('[data-lp="name2"]').textContent = name;
      q('[data-lp="city"]').textContent = city;
      q('[data-lp="city2"]').textContent = city;
      if (!tpl) return;
      q('[data-lp="subject"]').textContent = tpl.subject;
      var paras = tpl.paras.slice();
      var closer = paras.pop();
      q('[data-lp="body"]').innerHTML = paras
        .map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
      var personal = (paraInput.value || "").trim();
      q('[data-lp="para"]').innerHTML = personal
        ? "<p><em>" + esc(personal) + "</em></p>" : "";
      q('[data-lp="closer"]').innerHTML = "<p>" + esc(closer) + "</p>";
    }

    [nameInput, cityInput, paraInput].forEach(function (el) {
      el.addEventListener("input", render);
    });
    document.querySelectorAll('input[name="template"]').forEach(function (r) {
      r.addEventListener("change", function () {
        document.querySelectorAll(".tpl-option").forEach(function (o) {
          o.classList.toggle("checked", o.querySelector("input").checked);
        });
        render();
      });
    });
    render();
  }

  /* ---------- write page: tier radios + tip slider ---------- */
  document.querySelectorAll('input[name="tier"]').forEach(function (r) {
    r.addEventListener("change", function () {
      document.querySelectorAll(".tier-radio").forEach(function (o) {
        o.classList.toggle("checked", o.querySelector("input").checked);
      });
    });
  });
  var tip = document.getElementById("f-tip");
  var tipValue = document.getElementById("tip-value");
  if (tip && tipValue) {
    tip.addEventListener("input", function () {
      tipValue.textContent = "₹" + tip.value;
    });
  }

  /* ---------- copy caption buttons ---------- */
  document.querySelectorAll(".copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(btn.dataset.copy).then(function () {
        var was = btn.textContent;
        btn.textContent = "Copied ✓";
        setTimeout(function () { btn.textContent = was; }, 1500);
      });
    });
  });

  /* ---------- Web Share API (status page) ---------- */
  var shareBtn = document.getElementById("share-btn");
  if (shareBtn) {
    if (navigator.share) {
      shareBtn.addEventListener("click", function () {
        navigator.share({
          title: "Janata Ki Baat",
          text: shareBtn.dataset.text,
          url: shareBtn.dataset.url,
        }).catch(function () { /* user closed the sheet — fine */ });
      });
    } else {
      shareBtn.addEventListener("click", function () {
        navigator.clipboard.writeText(
          shareBtn.dataset.text + " " + shareBtn.dataset.url);
        shareBtn.textContent = "Link copied ✓ — paste it anywhere";
      });
    }
  }

  /* ---------- hide UPI intent button on desktop ---------- */
  var upiBtn = document.getElementById("upi-intent");
  if (upiBtn && !/Android|iPhone|iPad/i.test(navigator.userAgent)) {
    upiBtn.style.display = "none";
  }
})();
