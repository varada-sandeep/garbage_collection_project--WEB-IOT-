// DOM Content Loaded Event
document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alerts after 5 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
      // Create a Bootstrap alert instance and hide it
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);

  // Initialize all tooltips
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Add event listener to worker assignment form
  const assignForms = document.querySelectorAll(
    'form[action*="assign_worker"]'
  );
  assignForms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const select = form.querySelector('select[name="worker_id"]');
      if (!select.value) {
        e.preventDefault();
        alert("Please select a worker to assign");
      }
    });
  });

  // Highlight new alerts (if any)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("highlight")) {
    const alertId = urlParams.get("highlight");
    const alertElement = document.getElementById("alert-" + alertId);
    if (alertElement) {
      alertElement.classList.add("bg-light");
      alertElement.scrollIntoView({ behavior: "smooth" });

      // Remove highlight after 3 seconds
      setTimeout(function () {
        alertElement.classList.remove("bg-light");
      }, 3000);
    }
  }

  // Setup real-time updates for dashboard (simulated)
  if (
    window.location.pathname === "/" ||
    window.location.pathname === "/dashboard"
  ) {
    setupDashboardRefresh();
  }
});

// Function to set up dashboard auto-refresh
function setupDashboardRefresh() {
  // Update time every second
  const timeElement = document.getElementById("current-time");
  const lastUpdatedElement = document.getElementById("last-updated");

  if (timeElement && lastUpdatedElement) {
    function updateTime() {
      const now = new Date();
      timeElement.textContent = now.toLocaleTimeString();
      lastUpdatedElement.textContent = now.toLocaleTimeString();
    }

    // Initial update
    updateTime();

    // Update every second
    setInterval(updateTime, 1000);
  }

  // Refresh page every 30 seconds to get updated data
  setTimeout(function () {
    window.location.reload();
  }, 30000);
}

// Function to confirm deletions
function confirmDelete(message) {
  return confirm(message || "Are you sure you want to delete this item?");
}

// Function to simulate ESP32 alert (for testing purposes)
function simulateAlert() {
  const binId = document.getElementById("test-bin-id").value;
  const fillLevel = document.getElementById("test-fill-level").value;

  if (!binId || !fillLevel) {
    alert("Please enter both Bin ID and Fill Level");
    return;
  }

  const data = {
    bin_id: binId,
    fill_level: parseInt(fillLevel),
  };

  fetch("/api/alert", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => {
      alert("Alert sent successfully! Severity: " + data.severity);
      window.location.reload();
    })
    .catch((error) => {
      alert("Error sending alert: " + error);
    });
}
