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

        // Re-enable buttons (Back always enabled after advancing past lead 1)
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        var backBtn = getEl("btn-back");
        if (backBtn) backBtn.disabled = false;
        busy = false;
      })
      .catch((err) => {
        console.error("Error logging action:", err);
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        var backBtn = getEl("btn-back");
        if (backBtn) backBtn.disabled = false;
        busy = false;
      });
  }

  // Copy flyer image to clipboard
  function copyFlyer() {
    const img = getEl("flyer-img");
    const btn = getEl("btn-copy-flyer");
    const label = getEl("copy-flyer-label");
    if (!img || !btn) return;

    // Draw image to canvas to get a PNG blob
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);

    canvas.toBlob(function (blob) {
      if (!blob) return;
      navigator.clipboard
        .write([new ClipboardItem({ "image/png": blob })])
        .then(function () {
          label.textContent = "Copied!";
          btn.classList.remove("bg-amber-500", "hover:bg-amber-400");
          btn.classList.add("bg-green-500");
          setTimeout(function () {
            label.textContent = "Copy Flyer";
            btn.classList.remove("bg-green-500");
            btn.classList.add("bg-amber-500", "hover:bg-amber-400");
          }, 2000);
        })
        .catch(function (err) {
          console.error("Clipboard copy failed:", err);
          label.textContent = "Failed";
          setTimeout(function () {
            label.textContent = "Copy Flyer";
          }, 2000);
        });
    }, "image/png");
  }

  // Go back to previous lead
  function goBack() {
    if (busy) return;
    var btn = getEl("btn-back");
    if (btn && btn.disabled) return;
    busy = true;

    var sessionId = getEl("session-id").value;

    // Disable all buttons
    getEl("btn-sent").disabled = true;
    getEl("btn-skip").disabled = true;
    if (btn) btn.disabled = true;

    fetch("/api/outreach/back", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: parseInt(sessionId) }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          console.error("Back error:", data.error);
          busy = false;
          getEl("btn-sent").disabled = false;
          getEl("btn-skip").disabled = false;
          return;
        }

        // Update UI with previous lead
        var lead = data.lead;
        getEl("lead-id").value = lead.id;
        getEl("lead-name").textContent = lead.name;
        getEl("lead-company").textContent = lead.company;
        getEl("lead-city").textContent = lead.city;
        getEl("lead-rank").textContent = lead.rank;
        getEl("lead-volume").textContent = lead.volume;
        getEl("progress-current").textContent = data.current;
        getEl("btn-open").href = lead.profile_url;

        // Update progress bar
        var pct = (data.current / parseInt(getEl("progress-total").textContent)) * 100;
        getEl("progress-bar").style.width = pct + "%";

        // Re-enable buttons; disable Back if at first lead
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        if (btn) btn.disabled = (data.current <= 1);
        busy = false;
      })
      .catch(function (err) {
        console.error("Error going back:", err);
        getEl("btn-sent").disabled = false;
        getEl("btn-skip").disabled = false;
        if (btn) btn.disabled = false;
        busy = false;
      });
  }

  // Expose to onclick handlers
  window.logAction = logAction;
  window.copyFlyer = copyFlyer;
  window.goBack = goBack;

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
      case "c":
        copyFlyer();
        break;
      case "b":
        goBack();
        break;
    }
  });
})();
