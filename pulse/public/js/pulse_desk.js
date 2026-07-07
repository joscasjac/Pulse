// One-click launcher: when the "Pulse" workspace is opened in the Desk,
// send the browser straight to the Pulse SPA at /pulse.
(function () {
  function go() {
    try {
      var p = (window.location.pathname || "").toLowerCase().replace(/\/+$/, "");
      if (p === "/app/pulse") {
        window.location.replace("/pulse");
      }
    } catch (e) {}
  }
  document.addEventListener("DOMContentLoaded", go);
  if (window.frappe && frappe.router && frappe.router.on) {
    frappe.router.on("change", go);
  }
  // fallback in case the router isn't ready yet on first paint
  setTimeout(go, 150);
})();
