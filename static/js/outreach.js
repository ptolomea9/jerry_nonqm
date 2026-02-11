// Outreach session: AJAX actions + keyboard shortcuts
(function () {
  let busy = false;

  function getEl(id) {
    return document.getElementById(id);
  }

  function logAction(result) {
    if (busy) return;
    busy = true;

    const sessionId = getEl("session-id").value;
    const leadId = getEl("lead-id").value;
    const summaryUrl = getEl("summary-url").value;

    // Disable buttons
    getEl("btn-sent").disabled = true;
    getEl("btn-skip").disabled = true;

    fetch("/api/outreach/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: parseInt(sessionId),
        lead_id: parseInt(leadId),
        result: result,
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.done) {
          window.location.href = summaryUrl;
          return;
        }

        // Update UI with next lead
        const lead = data.lead;
        getEl("lead-id").value = lead.id;
        getEl("lead-name").textContent = lead.name;
        getEl("lead-company").textContent = lead.company;
        getEl("lead-city").textContent = lead.city;
        getEl("lead-rank").textContent = lead.rank;
        getEl("lead-volume").textContent = lead.volume;
        getEl("progress-current").textContent = data.current;
        getEl("btn-open").href = lead.profile_url;

        // Update progress bar
        const pct = (data.current / parseInt(getEl("progress-total").textContent)) * 100;
        getEl("progress-bar").style.width = pct + "%";

        // Re-enable buttons
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        busy = false;
      })
      .catch((err) => {
        console.error("Error logging action:", err);
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        busy = false;
      });
  }

  // Expose to onclick handlers
  window.logAction = logAction;

  // Keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    // Don't trigger if typing in an input
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    switch (e.key.toLowerCase()) {
      case "s":
        logAction("sent");
        break;
      case "x":
        logAction("skipped");
        break;
      case "o":
        getEl("btn-open").click();
        break;
    }
  });
})();
