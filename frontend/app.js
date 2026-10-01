/**
 * ==============================================================================
 * EchoSense Frontend Application Controller
 * ==============================================================================
 * Real-time WebSocket DOM binding, 60 FPS HTML5 Canvas Oscilloscope & Spectrum,
 * Device telemetry tracking, contact management, toast alerts, event filtering,
 * and dev bench testing.
 */

class EchoSenseApp {
  constructor() {
    this.ws = null;
    this.activeView = "dashboard";
    this.contacts = [];
    this.events = [];
    this.devices = [];
    this.activeAlert = null;
    this.reconnectTimer = null;

    // Analytics counters
    this.totalSoundsEvaluated = 0;
    this.activeFilter = "";
    this.searchQuery = "";

    // Live visualizer state
    this.canvas = null;
    this.ctx = null;
    this.animFrameId = null;
    this.visualizerEnergy = 0.05;
    this.targetVisualizerEnergy = 0.05;
    this.spectrumBands = new Array(32).fill(0.1);

    this.init();
  }

  init() {
    this.setupNavigation();
    this.setupVisualizer();
    this.initVirtualLedRing();
    this.connectWebSocket();
    this.fetchContacts();
    this.fetchEvents();
    this.fetchDevices();
    this.checkAudioSourceStatus();
    this.fetchNetworkInfo();
  }

  // --- HTML5 Canvas 60 FPS Audio Visualizer ---
  setupVisualizer() {
    this.canvas = document.getElementById("audio-visualizer-canvas");
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    // Handle high DPI displays
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width > 0) {
      this.canvas.width = rect.width * dpr;
      this.canvas.height = (rect.height || 90) * dpr;
      this.ctx.scale(dpr, dpr);
    }

    // Start 60fps render loop
    this.renderVisualizer = this.renderVisualizer.bind(this);
    this.animFrameId = requestAnimationFrame(this.renderVisualizer);
  }

  renderVisualizer(timestamp) {
    if (!this.canvas || !this.ctx) return;

    const width = this.canvas.clientWidth || 580;
    const height = this.canvas.clientHeight || 90;
    const ctx = this.ctx;

    // Smoothly interpolate current visualizer energy towards latest target RMS
    this.visualizerEnergy += (this.targetVisualizerEnergy - this.visualizerEnergy) * 0.15;
    const energy = Math.max(0.04, this.visualizerEnergy);

    // Clear background
    ctx.clearRect(0, 0, width, height);

    // 1. Draw Simulated Frequency Spectrum Bars in Background
    const numBars = 32;
    const barWidth = (width / numBars) - 3;
    const time = timestamp * 0.003;

    for (let i = 0; i < numBars; i++) {
      // Simulate realistic acoustic harmonics
      const baseFreq = Math.sin(time + i * 0.3) * 0.3 + 0.5;
      const targetHeight = (baseFreq * energy * height * 0.9) + 4;
      this.spectrumBands[i] += (targetHeight - this.spectrumBands[i]) * 0.2;

      const barH = Math.min(height - 10, Math.max(3, this.spectrumBands[i]));
      const x = i * (barWidth + 3);
      const y = height - barH;

      // Gradient color (Cyan to Violet)
      const grad = ctx.createLinearGradient(0, height, 0, 0);
      grad.addColorStop(0, "rgba(6, 182, 212, 0.15)");
      grad.addColorStop(0.7, "rgba(56, 189, 248, 0.45)");
      grad.addColorStop(1, "rgba(168, 85, 247, 0.8)");

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, [3, 3, 0, 0]);
      ctx.fill();
    }

    // 2. Draw Center Oscilloscope Waveform Line
    ctx.beginPath();
    ctx.lineWidth = 2.2;
    const lineGrad = ctx.createLinearGradient(0, 0, width, 0);
    lineGrad.addColorStop(0, "#06b6d4");
    lineGrad.addColorStop(0.5, "#38bdf8");
    lineGrad.addColorStop(1, "#a855f7");
    ctx.strokeStyle = lineGrad;

    const centerY = height / 2;
    const points = 48;
    const step = width / (points - 1);

    for (let i = 0; i < points; i++) {
      const x = i * step;
      const angle = (i * 0.25) + (time * 2.5);
      const waveOffset = Math.sin(angle) * Math.cos(angle * 0.5) * (energy * height * 0.45);
      const y = centerY + waveOffset;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Loop
    this.animFrameId = requestAnimationFrame(this.renderVisualizer);
  }

  // --- Real-Time WebSocket Connection ---
  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("[WS] Connected to EchoSense Hub.");
      document.getElementById("backend-status-text").innerText = "Backend: Connected";
      document.getElementById("dot-backend").className = "status-dot dot-online";
      document.getElementById("text-backend").innerText = "Connected";
      this.showToast("Connected to EchoSense Portal", "success");
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleWsMessage(data);
      } catch (err) {
        console.error("[WS] Error parsing message:", err);
      }
    };

    this.ws.onclose = () => {
      console.warn("[WS] Disconnected. Reconnecting in 2s...");
      document.getElementById("backend-status-text").innerText = "Backend: Offline";
      document.getElementById("dot-backend").className = "status-dot dot-offline";
      document.getElementById("text-backend").innerText = "Reconnecting...";
      
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error("[WS] Socket error:", err);
    };
  }

  handleWsMessage(data) {
    if (data.type === "INITIAL_SYNC") {
      if (data.devices) this.updateDeviceUI(data.devices);
      if (data.activeAlert) this.updateActiveAlertUI(data.activeAlert);
      if (data.latestTelemetry) this.updateTelemetryUI(data.latestTelemetry);
      if (data.recentEvents) this.updateQuickEventsTable(data.recentEvents);
    } 
    else if (data.type === "LIVE_TELEMETRY") {
      if (data.telemetry) this.updateTelemetryUI(data.telemetry);
      if (data.devices) this.updateDeviceUI(data.devices);
    } 
    else if (data.type === "DEVICE_UPDATE") {
      if (data.devices) this.updateDeviceUI(data.devices);
    }
    else if (data.type === "STATE_CHANGE") {
      this.updateActiveAlertUI(data.event);
      if (data.devices) this.updateDeviceUI(data.devices);
      this.fetchEvents(); // Refresh event log
    }
  }

  // --- Real-Time Telemetry Updates ---
  updateTelemetryUI(t) {
    this.totalSoundsEvaluated++;
    const countEl = document.getElementById("kpi-sounds-count");
    if (countEl) countEl.innerText = this.totalSoundsEvaluated.toLocaleString();

    // Update target energy for live canvas visualizer
    const rms = t.rms || 0.0;
    this.targetVisualizerEnergy = Math.min(1.0, rms * 4.5);

    // Current Sound Label
    const soundLabel = document.getElementById("current-sound-text");
    if (soundLabel) soundLabel.innerText = t.currentSound || "Monitoring";

    // Raw Class
    const rawClass = document.getElementById("metric-raw-class");
    if (rawClass) rawClass.innerText = t.rawLabel || "None";

    // Confidence
    const confEl = document.getElementById("confidence-percentage");
    if (confEl) {
      const confPct = Math.round((t.confidence || 0) * 100);
      confEl.innerText = `${confPct}%`;
    }

    // Status Tag & KPI Badge
    const tagEl = document.getElementById("sound-status-tag");
    const kpiBadge = document.getElementById("kpi-status-badge");
    const kpiState = document.getElementById("kpi-safety-state");
    const st = t.status || "NORMAL";

    if (tagEl) {
      tagEl.innerText = st;
      tagEl.className = "sound-status-tag";
      if (st === "NORMAL") tagEl.classList.add("tag-normal");
      else if (st === "VALIDATING") tagEl.classList.add("tag-validating");
      else if (st === "CONFIRMED") tagEl.classList.add("tag-warning");
      else if (st === "CRITICAL") tagEl.classList.add("tag-critical");
      else if (st === "SOS") tagEl.classList.add("tag-sos");
    }

    if (kpiBadge && kpiState) {
      kpiBadge.innerText = st;
      kpiState.innerText = st.charAt(0) + st.slice(1).toLowerCase();
      if (st === "NORMAL") {
        kpiState.style.color = "#34d399";
        kpiBadge.style.color = "#34d399";
        kpiBadge.style.background = "rgba(52,211,153,0.12)";
      } else if (st === "VALIDATING") {
        kpiState.style.color = "#22d3ee";
        kpiBadge.style.color = "#22d3ee";
        kpiBadge.style.background = "rgba(34,211,238,0.12)";
      } else if (st === "CONFIRMED" || st === "WARNING") {
        kpiState.style.color = "#eab308";
        kpiBadge.style.color = "#eab308";
        kpiBadge.style.background = "rgba(234,179,8,0.12)";
      } else {
        kpiState.style.color = "#ef4444";
        kpiBadge.style.color = "#ef4444";
        kpiBadge.style.background = "rgba(239,68,68,0.12)";
      }
    }

    // Audio Energy (RMS & dBFS)
    const meterFill = document.getElementById("meter-fill");
    const dbfsText = document.getElementById("rms-dbfs-value");
    if (meterFill && dbfsText) {
      const dbfs = t.dbfs || -96.0;
      dbfsText.innerText = `${dbfs} dBFS`;
      const widthPct = Math.min(100, Math.max(2, (rms / 0.15) * 100));
      meterFill.style.width = `${widthPct}%`;
    }

    // Validation Persistence Progress
    const valText = document.getElementById("validation-counter-text");
    const valFill = document.getElementById("validation-fill");
    if (valText && valFill && t.validation) {
      const confs = t.validation.confirmations || 0;
      const req = t.validation.required || 3;
      valText.innerText = `${confs} / ${req} confirmations`;
      valFill.style.width = `${t.validation.progressPct || 0}%`;
    }

    // SNR
    const snrEl = document.getElementById("metric-snr");
    if (snrEl && t.snr !== undefined) {
      snrEl.innerText = `${t.snr} dB`;
    }

    // Update active audio source badge & buttons
    const activeSrc = t.activeSource || t.device || "HOST_LAPTOP_MIC";
    this.updateSourceUI(activeSrc);

    // Update Live YAMNet Top 5 Predictions Multi-Class Breakdown
    if (t.topPredictions && t.topPredictions.length > 0) {
      this.renderTopPredictions(t.topPredictions);
    }

    // Real-time LED feedback on validated sound events
    if (t.validatedEvent && t.validatedEvent.rgbColor) {
      this.updateVirtualLedRing(t.validatedEvent.rgbColor, t.validatedEvent.rgbMode, t.validatedEvent.displayLabel);
    }
  }

  // --- Active Alert Banner ---
  updateActiveAlertUI(event) {
    if (event && event.rgbColor) {
      this.updateVirtualLedRing(event.rgbColor, event.rgbMode, event.displayLabel);
    }

    const banner = document.getElementById("emergency-banner");
    if (!banner) return;

    if (!event || event.severity === "NORMAL" || event.priority > 2) {
      banner.classList.remove("active", "sos-mode");
      if (!event || event.severity === "NORMAL") {
        this.updateVirtualLedRing([255, 255, 255], "WHITE_BREATH", "Ready");
      }
      return;
    }

    banner.classList.add("active");
    if (event.category === "SOS" || event.priority === 0) {
      banner.classList.add("sos-mode");
      document.getElementById("emergency-title").innerText = "🚨 PHYSICAL SOS EMERGENCY ACTIVATED";
    } else {
      banner.classList.remove("sos-mode");
      document.getElementById("emergency-title").innerText = "CRITICAL ALERT DETECTED";
    }

    document.getElementById("emergency-event-label").innerText = event.displayLabel || "-";
    document.getElementById("emergency-confidence").innerText = `${Math.round((event.confidence || 1) * 100)}%`;
    
    const notifyStr = event.notificationRequired 
      ? `${event.contactsNotified || 0} / ${event.totalContacts || 5} Contacts Notified` 
      : "Not Required";
    document.getElementById("emergency-contacts-notified").innerText = notifyStr;
  }

  // --- Device Statuses ---
  updateDeviceUI(devices) {
    this.devices = devices;
    const esp32 = devices.find(d => d.type === "ESP32");
    const esp8266 = devices.find(d => d.type === "ESP8266");

    // Top status dots
    if (esp32) {
      const isOnline = esp32.status === "ONLINE";
      document.getElementById("dot-esp32").className = `status-dot ${isOnline ? 'dot-online' : 'dot-offline'}`;
      document.getElementById("text-esp32").innerText = isOnline 
        ? `Online (${esp32.secondsSinceHeartbeat !== null ? esp32.secondsSinceHeartbeat + 's' : 'active'})` 
        : "Offline";

      const b32 = document.getElementById("esp32-badge");
      if (b32) {
        b32.innerText = esp32.status;
        b32.style.color = isOnline ? "#34d399" : "#f87171";
      }
      this.setVal("dev-esp32-ip", esp32.ip || "--");
      this.setVal("dev-esp32-rssi", `${esp32.rssi || 0} dBm`);
      this.setVal("dev-esp32-uptime", `${esp32.uptimeSeconds || 0}s`);
      this.setVal("dev-esp32-hb", esp32.lastHeartbeatFormatted || "Never");
      this.setVal("dev-esp32-mic", esp32.sensors?.inmp441 || "STREAMING");
      this.setVal("dev-esp32-sos", esp32.sensors?.sosButton || "READY");

      this.updateRssiMeter("dev-esp32-rssi-meter", esp32.rssi);
    }

    if (esp8266) {
      const isOnline = esp8266.status === "ONLINE";
      document.getElementById("dot-esp8266").className = `status-dot ${isOnline ? 'dot-online' : 'dot-offline'}`;
      document.getElementById("text-esp8266").innerText = isOnline 
        ? `Online (${esp8266.secondsSinceHeartbeat !== null ? esp8266.secondsSinceHeartbeat + 's' : 'active'})` 
        : "Offline";

      const b8266 = document.getElementById("esp8266-badge");
      if (b8266) {
        b8266.innerText = esp8266.status;
        b8266.style.color = isOnline ? "#34d399" : "#f87171";
      }
      this.setVal("dev-esp8266-ip", esp8266.ip || "--");
      this.setVal("dev-esp8266-rssi", `${esp8266.rssi || 0} dBm`);
      this.setVal("dev-esp8266-uptime", `${esp8266.uptimeSeconds || 0}s`);
      this.setVal("dev-esp8266-hb", esp8266.lastHeartbeatFormatted || "Never");
      this.setVal("dev-esp8266-rgb", esp8266.actuators?.rgbRing || "ACTIVE (D2)");
      this.setVal("dev-esp8266-buzzer", esp8266.actuators?.buzzer || "READY (D1)");

      this.updateRssiMeter("dev-esp8266-rssi-meter", esp8266.rssi);
    }
  }

  updateRssiMeter(elementId, rssi) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.className = "rssi-meter";
    if (rssi >= -60) el.classList.add("rssi-strong");
    else if (rssi >= -70) el.classList.add("rssi-good");
    else if (rssi >= -80) el.classList.add("rssi-fair");
    else el.classList.add("rssi-weak");
  }

  setVal(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
  }

  // --- Navigation ---
  setupNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
      item.addEventListener("click", () => {
        const view = item.getAttribute("data-view");
        this.switchView(view);
      });
    });
  }

  switchView(viewName) {
    this.activeView = viewName;

    document.querySelectorAll(".nav-item").forEach(item => {
      if (item.getAttribute("data-view") === viewName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    const titles = {
      dashboard: "Dashboard",
      events: "Historical Events Log",
      contacts: "Emergency Contacts",
      devices: "Connected IoT Hardware",
      settings: "System Settings",
      "dev-test": "Development Bench Testing"
    };
    document.getElementById("current-view-title").innerText = titles[viewName] || "Dashboard";

    document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active-view"));
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add("active-view");

    if (viewName === "events") this.fetchEvents();
    if (viewName === "contacts") this.fetchContacts();
    if (viewName === "devices") this.fetchDevices();
  }

  // --- Events API, Filtering, Search & Export ---
  async fetchEvents(filter = null) {
    try {
      const filterVal = (filter !== null) ? filter : (document.getElementById("event-severity-filter")?.value || "");
      const url = filterVal ? `/api/events?severity=${filterVal}` : `/api/events`;
      const res = await fetch(url);
      const data = await res.json();
      this.events = data;

      this.updateQuickEventsTable(data.slice(0, 5));
      this.applyEventFilters();
    } catch (e) {
      console.error("Error fetching events:", e);
    }
  }

  filterEvents(severity) {
    this.activeFilter = severity;
    this.fetchEvents(severity);
  }

  searchEvents(query) {
    this.searchQuery = (query || "").toLowerCase().trim();
    this.applyEventFilters();
  }

  applyEventFilters() {
    let filtered = this.events;
    if (this.searchQuery) {
      filtered = filtered.filter(e => 
        (e.displayLabel && e.displayLabel.toLowerCase().includes(this.searchQuery)) ||
        (e.rawLabel && e.rawLabel.toLowerCase().includes(this.searchQuery)) ||
        (e.severity && e.severity.toLowerCase().includes(this.searchQuery)) ||
        (e.device && e.device.toLowerCase().includes(this.searchQuery))
      );
    }
    this.updateFullEventsTable(filtered);
  }

  exportEventsCSV() {
    if (!this.events || this.events.length === 0) {
      this.showToast("No events to export", "warning");
      return;
    }

    const headers = ["Time", "Display Label", "Raw Label", "Confidence", "Severity", "Device", "WhatsApp Status", "Contacts Notified"];
    const rows = this.events.map(e => [
      `"${e.formattedTime || ''}"`,
      `"${e.displayLabel || ''}"`,
      `"${e.rawLabel || ''}"`,
      `"${Math.round((e.confidence || 0) * 100)}%"`,
      `"${e.severity || ''}"`,
      `"${e.device || ''}"`,
      `"${e.notificationStatus || ''}"`,
      `"${e.contactsNotified || 0}/${e.totalContacts || 0}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `echosense_events_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast("Event log exported to CSV", "success");
  }

  exportEventsJSON() {
    if (!this.events || this.events.length === 0) {
      this.showToast("No events to export", "warning");
      return;
    }
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.events, null, 2));
    const link = document.createElement("a");
    link.setAttribute("href", dataStr);
    link.setAttribute("download", `echosense_events_${new Date().toISOString().slice(0,10)}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast("Event log exported to JSON", "success");
  }

  updateQuickEventsTable(events) {
    const tbody = document.getElementById("quick-events-table-body");
    if (!tbody) return;

    if (!events || events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No events recorded yet</td></tr>`;
      return;
    }

    tbody.innerHTML = events.map(e => `
      <tr>
        <td style="font-family:var(--font-mono); font-size:0.8rem;">${e.formattedTime || '--'}</td>
        <td style="font-weight:600; color:#fff;">${e.displayLabel}</td>
        <td><span class="status-pill" style="color:${this.getSeverityColor(e.severity)};">${e.severity}</span></td>
        <td style="font-family:var(--font-mono);">${Math.round(e.confidence * 100)}%</td>
      </tr>
    `).join("");
  }

  updateFullEventsTable(events) {
    const tbody = document.getElementById("full-events-table-body");
    if (!tbody) return;

    if (!events || events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:24px;">No matching events found.</td></tr>`;
      return;
    }

    tbody.innerHTML = events.map(e => `
      <tr>
        <td style="font-family:var(--font-mono);">${e.formattedTime || '--'}</td>
        <td style="font-weight:600; color:#fff;">${e.displayLabel}</td>
        <td style="color:var(--text-muted);">${e.rawLabel || '-'}</td>
        <td style="font-family:var(--font-mono);">${Math.round(e.confidence * 100)}%</td>
        <td><span class="status-pill" style="color:${this.getSeverityColor(e.severity)};">${e.severity}</span></td>
        <td>${e.device}</td>
        <td><span class="status-pill">${e.notificationStatus} (${e.contactsNotified}/${e.totalContacts})</span></td>
      </tr>
    `).join("");
  }

  getSeverityColor(sev) {
    switch (sev) {
      case "SOS": return "#ec4899";
      case "CRITICAL": return "#ef4444";
      case "WARNING": return "#eab308";
      case "INFO": return "#f97316";
      default: return "#3b82f6";
    }
  }

  // --- Contacts API ---
  async fetchContacts() {
    try {
      const res = await fetch("/api/contacts");
      this.contacts = await res.json();
      this.renderContactsTable();
    } catch (e) {
      console.error("Error fetching contacts:", e);
    }
  }

  renderContactsTable() {
    const tbody = document.getElementById("contacts-table-body");
    const addBtn = document.getElementById("btn-add-contact");
    if (!tbody) return;

    if (addBtn) {
      addBtn.disabled = this.contacts.length >= 5;
      addBtn.title = this.contacts.length >= 5 ? "Maximum 5 contacts configured" : "Add Emergency Contact";
    }

    const quickContacts = document.getElementById("quick-contacts-count");
    if (quickContacts) {
      const activeCount = this.contacts.filter(c => c.enabled).length;
      quickContacts.innerText = `${activeCount} Contact${activeCount === 1 ? '' : 's'} Active`;
    }

    if (this.contacts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:24px;">No emergency contacts configured yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.contacts.map(c => `
      <tr>
        <td style="font-weight:700; font-family:var(--font-mono);">${c.priority}</td>
        <td style="font-weight:600; color:#fff;">${c.name}</td>
        <td style="font-family:var(--font-mono);">${c.phoneNumber}</td>
        <td>${c.relationship || 'Caregiver'}</td>
        <td>
          <button class="btn btn-sm ${c.enabled ? 'btn-primary' : 'btn-outline'}" onclick="app.toggleContact('${c.id}', ${!c.enabled})">
            ${c.enabled ? 'Active' : 'Disabled'}
          </button>
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="app.editContact('${c.id}')">Edit</button>
          <button class="btn btn-outline btn-sm" style="color:#ef4444; border-color:rgba(239,68,68,0.3);" onclick="app.deleteContact('${c.id}')">Delete</button>
        </td>
      </tr>
    `).join("");
  }

  openAddContactModal() {
    document.getElementById("modal-title").innerText = "Add Emergency Contact";
    document.getElementById("contact-id").value = "";
    document.getElementById("contact-name").value = "";
    document.getElementById("contact-phone").value = "";
    document.getElementById("contact-relation").value = "";
    document.getElementById("contact-priority").value = Math.min(5, this.contacts.length + 1);
    document.getElementById("contact-modal").classList.add("open");
  }

  closeContactModal() {
    document.getElementById("contact-modal").classList.remove("open");
  }

  editContact(id) {
    const c = this.contacts.find(item => item.id === id);
    if (!c) return;

    document.getElementById("modal-title").innerText = "Edit Emergency Contact";
    document.getElementById("contact-id").value = c.id;
    document.getElementById("contact-name").value = c.name;
    document.getElementById("contact-phone").value = c.phoneNumber;
    document.getElementById("contact-relation").value = c.relationship || "";
    document.getElementById("contact-priority").value = c.priority || 1;
    document.getElementById("contact-modal").classList.add("open");
  }

  async saveContact(event) {
    event.preventDefault();
    const id = document.getElementById("contact-id").value;
    const name = document.getElementById("contact-name").value.trim();
    const phone = document.getElementById("contact-phone").value.trim();
    const relation = document.getElementById("contact-relation").value.trim();
    const priority = parseInt(document.getElementById("contact-priority").value) || 1;

    try {
      if (id) {
        await fetch(`/api/contacts/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, phoneNumber: phone, relationship: relation, priority })
        });
        this.showToast(`Contact "${name}" updated`, "success");
      } else {
        const newId = `c_${Date.now()}`;
        const res = await fetch("/api/contacts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: newId, name, phoneNumber: phone, relationship: relation, priority, enabled: true })
        });
        if (!res.ok) {
          const err = await res.json();
          this.showToast(err.detail || "Failed to add contact", "error");
          return;
        }
        this.showToast(`Contact "${name}" added`, "success");
      }
      this.closeContactModal();
      this.fetchContacts();
    } catch (e) {
      console.error("Error saving contact:", e);
      this.showToast("Error saving contact: " + e.message, "error");
    }
  }

  async toggleContact(id, newStatus) {
    try {
      await fetch(`/api/contacts/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: newStatus })
      });
      this.fetchContacts();
      this.showToast(`Contact status changed`, "info");
    } catch (e) {
      console.error("Error toggling contact:", e);
    }
  }

  async deleteContact(id) {
    if (!confirm("Remove this emergency contact?")) return;
    try {
      await fetch(`/api/contacts/${id}`, { method: "DELETE" });
      this.fetchContacts();
      this.showToast("Contact deleted", "info");
    } catch (e) {
      console.error("Error deleting contact:", e);
    }
  }

  openTestNotificationModal() {
    document.getElementById("test-notify-modal").classList.add("open");
  }

  closeTestModal() {
    document.getElementById("test-notify-modal").classList.remove("open");
  }

  async confirmSendTestNotification() {
    this.closeTestModal();
    try {
      const res = await fetch("/api/contacts/test", { method: "POST" });
      const data = await res.json();
      const count = data.results?.contactsSuccess || 0;
      this.showToast(`Test notification dispatched! (${count} contacts)`, "success");
    } catch (e) {
      console.error("Error sending test notification:", e);
      this.showToast("Failed to dispatch test notification", "error");
    }
  }

  // --- Device Telemetry API ---
  async fetchDevices() {
    try {
      const res = await fetch("/api/devices");
      const devices = await res.json();
      this.updateDeviceUI(devices);
    } catch (e) {
      console.error("Error fetching devices:", e);
    }
  }

  // --- Alert Controls ---
  async resetAlert() {
    try {
      await fetch("/api/events/reset", { method: "POST" });
      this.updateActiveAlertUI(null);
      this.showToast("Alert state reset to Normal", "info");
    } catch (e) {
      console.error("Error resetting alert:", e);
    }
  }

  async triggerSosManual() {
    if (!confirm("TRIGGER EMERGENCY SOS?\nThis will activate urgent visual strobes, sound physical alarms, and alert all configured contacts immediately.")) return;
    try {
      await fetch("/api/events/sos", { method: "POST" });
      this.showToast("🚨 EMERGENCY SOS BROADCASTED!", "error");
    } catch (e) {
      console.error("Error triggering SOS:", e);
    }
  }

  // --- Dev Bench Testing API ---
  async devTrigger(action) {
    const logBox = document.getElementById("dev-console-log");
    const appendLog = (msg) => {
      const time = new Date().toLocaleTimeString();
      logBox.innerHTML = `[${time}] ${msg}<br>` + logBox.innerHTML;
    };

    appendLog(`Executing: ${action}...`);

    try {
      const res = await fetch("/api/test/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      appendLog(`Result: ${data.result || 'Success'}`);
      this.showToast(`Bench action: ${action}`, "info");
      this.fetchDevices();
    } catch (e) {
      appendLog(`Error: ${e.message}`);
      this.showToast(`Error: ${e.message}`, "error");
    }
  }

  // --- Audio Source Selection & Laptop Mic Controls ---
  async checkAudioSourceStatus() {
    try {
      const res = await fetch("/api/audio/source");
      const data = await res.json();
      this.updateSourceUI(data.activeSource);
    } catch (e) {
      console.debug("Could not check audio source status:", e);
    }
  }

  async selectAudioSource(source) {
    try {
      const res = await fetch("/api/audio/source/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source })
      });
      const data = await res.json();
      this.updateSourceUI(data.activeSource);
      const friendlyName = data.activeSource === "HOST_LAPTOP_MIC" ? "Host Laptop Microphone (Main Active)" : "ESP32 (INMP441 Wireless)";
      this.showToast(`Audio Source Active: ${friendlyName}`, "success");
    } catch (e) {
      console.error("Error setting audio source:", e);
      this.showToast(`Source Switch Error: ${e.message}`, "error");
    }
  }

  updateSourceUI(activeSource) {
    const isLaptop = (activeSource || "").toUpperCase().includes("LAPTOP") || (activeSource || "").toUpperCase().includes("MIC");
    const btnLaptop = document.getElementById("src-btn-laptop");
    const btnEsp32 = document.getElementById("src-btn-esp32");
    const badge = document.getElementById("active-source-badge");
    const micDot = document.getElementById("dot-mic");
    const micText = document.getElementById("text-mic");

    if (btnLaptop && btnEsp32) {
      if (isLaptop) {
        btnLaptop.classList.add("active");
        btnEsp32.classList.remove("active");
        if (badge) badge.innerText = "🎙️ Host Laptop Mic (Active)";
        if (micText) micText.innerText = "Host Laptop Mic (Main)";
        if (micDot) micDot.className = "status-dot dot-online";
      } else {
        btnEsp32.classList.add("active");
        btnLaptop.classList.remove("active");
        if (badge) badge.innerText = "📡 ESP32 INMP441 (Active)";
        if (micText) micText.innerText = "ESP32 (INMP441)";
        if (micDot) micDot.className = "status-dot dot-online";
      }
    }
  }

  // --- Real-Time Top 5 Multi-Class Predictions Rendering ---
  renderTopPredictions(preds) {
    const container = document.getElementById("top-predictions-container");
    if (!container) return;

    if (!preds || preds.length === 0) {
      container.innerHTML = `<div style="font-size:0.82rem; color:var(--text-muted); text-align:center; padding:10px;">Listening for sounds...</div>`;
      return;
    }

    let html = "";
    preds.slice(0, 5).forEach((p, idx) => {
      const pct = Math.round((p.score || 0) * 100);
      const label = p.label || "Unknown";

      // Color scheme based on acoustic hazard/alert tier
      let barGrad = "linear-gradient(90deg, #06b6d4, #3b82f6)";
      const lower = label.toLowerCase();
      if (lower.includes("alarm") || lower.includes("siren") || lower.includes("smoke") || lower.includes("glass") || lower.includes("scream") || lower.includes("distress") || lower.includes("explosion") || lower.includes("gun")) {
        barGrad = "linear-gradient(90deg, #ef4444, #f43f5e)";
      } else if (lower.includes("doorbell") || lower.includes("chime") || lower.includes("knock") || lower.includes("horn") || lower.includes("cough")) {
        barGrad = "linear-gradient(90deg, #eab308, #f59e0b)";
      } else if (lower.includes("dog") || lower.includes("bark") || lower.includes("cat") || lower.includes("clap") || lower.includes("laughter") || lower.includes("telephone")) {
        barGrad = "linear-gradient(90deg, #f97316, #fb923c)";
      } else if (lower.includes("music") || lower.includes("sing") || lower.includes("guitar") || lower.includes("piano")) {
        barGrad = "linear-gradient(90deg, #10b981, #06b6d4)";
      }

      html += `
        <div class="prediction-row">
          <div class="prediction-info">
            <span class="prediction-name">
              <span class="prediction-rank">#${idx + 1}</span>
              <span>${label}</span>
            </span>
            <span class="prediction-score">${pct}%</span>
          </div>
          <div class="prediction-bar-track">
            <div class="prediction-bar-fill" style="width: ${Math.max(3, pct)}%; background: ${barGrad};"></div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  }

  // --- WhatsApp Test Alert Dispatch ---
  async sendTestWhatsApp() {
    try {
      this.showToast("Dispatching verification WhatsApp alert...", "info");
      const res = await fetch("/api/contacts/test", { method: "POST" });
      const data = await res.json();
      const count = data.results?.contactsSuccess || (data.results?.contactsTotal || 0);
      this.showToast(`WhatsApp Alert Dispatched (${count} recipients notified)`, "success");
      this.fetchContacts();
    } catch (e) {
      this.showToast(`WhatsApp Error: ${e.message}`, "error");
    }
  }

  async toggleLaptopMic() {
    await this.selectAudioSource("HOST_LAPTOP_MIC");
  }

  // --- Virtual WS2812 16-LED Ring Visualizer Engine ---
  initVirtualLedRing() {
    const ringEl = document.getElementById("virtual-led-ring");
    if (!ringEl) return;

    if (ringEl.querySelectorAll(".virtual-led-node").length > 0) return;

    const radius = 48; // px radius from center (120x120 ring)
    const centerX = 60, centerY = 60;
    const numLeds = 16;

    for (let i = 0; i < numLeds; i++) {
      const angle = ((i * 360 / numLeds) - 90) * (Math.PI / 180);
      const x = Math.round(centerX + radius * Math.cos(angle) - 6);
      const y = Math.round(centerY + radius * Math.sin(angle) - 6);

      const node = document.createElement("div");
      node.className = "virtual-led-node";
      node.id = `v-led-${i}`;
      node.style.left = `${x}px`;
      node.style.top = `${y}px`;
      ringEl.appendChild(node);
    }

    this.updateVirtualLedRing([255, 255, 255], "WHITE_BREATH", "Ready");
  }

  updateVirtualLedRing(rgbColor, rgbMode = "WHITE_BREATH", label = "") {
    if (!rgbColor || !Array.isArray(rgbColor)) rgbColor = [255, 255, 255];

    const r = Math.round(rgbColor[0] ?? 0);
    const g = Math.round(rgbColor[1] ?? 255);
    const b = Math.round(rgbColor[2] ?? 80);

    const rgbStr = `rgb(${r}, ${g}, ${b})`;
    const glowStr = `rgba(${r}, ${g}, ${b}, 0.75)`;
    const ambientGlowStr = `rgba(${r}, ${g}, ${b}, 0.35)`;

    // Update diffuse background glow on wrapper
    const wrapper = document.getElementById("virtual-led-container");
    if (wrapper) {
      wrapper.style.setProperty("--ring-glow-color", ambientGlowStr);
    }

    // Update state pill & hex text
    const modeBadge = document.getElementById("led-mode-badge");
    if (modeBadge) {
      modeBadge.innerText = rgbMode || "SOLID";
      modeBadge.style.color = rgbStr;
      modeBadge.style.borderColor = `rgba(${r}, ${g}, ${b}, 0.4)`;
      modeBadge.style.background = `rgba(${r}, ${g}, ${b}, 0.12)`;
    }

    const hexText = document.getElementById("led-color-hex");
    if (hexText) hexText.innerText = `RGB(${r}, ${g}, ${b})`;

    const swatch = document.getElementById("led-color-swatch");
    if (swatch) swatch.style.backgroundColor = rgbStr;

    // Center icon & state label
    const centerIcon = document.getElementById("ring-center-icon");
    const centerState = document.getElementById("ring-center-state");
    if (centerState) centerState.innerText = (label || rgbMode || "Ready").substring(0, 10);

    if (centerIcon) {
      if (rgbMode.includes("EMERGENCY") || rgbMode.includes("STROBE") || (r > 200 && g < 50)) {
        centerIcon.innerText = "🚨";
      } else if (rgbMode.includes("WHITE") || (r > 235 && g > 235 && b > 235)) {
        centerIcon.innerText = "⚪";
      } else if (rgbMode.includes("GLASS") || rgbMode.includes("SPARKLE")) {
        centerIcon.innerText = "✨";
      } else if (rgbMode.includes("CYAN") || (b > 200 && r < 50)) {
        centerIcon.innerText = "💧";
      } else if (rgbMode.includes("YELLOW") || rgbMode.includes("AMBER")) {
        centerIcon.innerText = "🟡";
      } else if (rgbMode.includes("PURPLE") || (r > 150 && b > 150)) {
        centerIcon.innerText = "🟣";
      } else if (rgbMode.includes("PEACH") || (r > 200 && g > 120 && b < 100)) {
        centerIcon.innerText = "🍑";
      } else if (rgbMode.includes("BLUE")) {
        centerIcon.innerText = "🌊";
      } else {
        centerIcon.innerText = "⚪";
      }
    }

    // Update container animation classes for visual breathing/pulsing
    const ringEl = document.getElementById("virtual-led-ring");
    if (ringEl) {
      ringEl.classList.remove("ring-mode-pulse", "ring-mode-strobe", "ring-mode-sparkle", "ring-mode-chase");
      if (rgbMode.includes("PULSE") || rgbMode.includes("BREATH")) ringEl.classList.add("ring-mode-pulse");
      else if (rgbMode.includes("STROBE") || rgbMode.includes("EMERGENCY")) ringEl.classList.add("ring-mode-strobe");
      else if (rgbMode.includes("SPARKLE")) ringEl.classList.add("ring-mode-sparkle");
      else if (rgbMode.includes("CHASE")) ringEl.classList.add("ring-mode-chase");
    }

    // Smooth color crossfade on all 16 virtual NeoPixel nodes
    for (let i = 0; i < 16; i++) {
      const node = document.getElementById(`v-led-${i}`);
      if (node) {
        node.style.backgroundColor = rgbStr;
        node.style.boxShadow = `0 0 10px ${glowStr}, 0 0 3px #fff`;
      }
    }
  }

  async triggerLedColor(rgbArray, mode, label, priority = 3, buzzerPattern = "OFF") {
    try {
      this.updateVirtualLedRing(rgbArray, mode, label);
      this.showToast(`Triggering LED: ${mode} (${label})`, "info");
      
      const payload = {
        action: "TEST_CUSTOM_COLOR",
        rgbColor: rgbArray,
        rgbMode: mode,
        displayLabel: label,
        priority: priority,
        buzzerPattern: buzzerPattern
      };
      
      const res = await fetch("/api/test/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      console.log("[LED Trigger Response]", data);
    } catch (e) {
      console.error("[LED Trigger Error]", e);
    }
  }

  // --- Emergency SOS & Acknowledge / Reset Engine ---
  async resetAlert() {
    try {
      this.showToast("Resetting alert state to Ambient White...", "info");
      const res = await fetch("/api/events/reset", { method: "POST" });
      const data = await res.json();
      this.activeAlert = null;
      this.updateActiveAlertUI(null);
      this.updateVirtualLedRing([255, 255, 255], "WHITE_BREATH", "Ready");
      this.showToast("System Reset: Ambient White (Silence/Normal)", "success");
    } catch (err) {
      console.error("Error resetting alert:", err);
      this.showToast("Failed to reset alert", "error");
    }
  }

  async triggerSosManual() {
    try {
      this.showToast("🚨 Triggering Physical Emergency SOS...", "warning");
      const res = await fetch("/api/events/sos?source=DASHBOARD_SOS", { method: "POST" });
      const data = await res.json();
      if (data.event) {
        this.activeAlert = data.event;
        this.updateActiveAlertUI(data.event);
      }
      this.showToast("🚨 EMERGENCY SOS BROADCAST SENT!", "error");
    } catch (err) {
      console.error("Error triggering SOS:", err);
      this.showToast("Failed to trigger SOS", "error");
    }
  }

  // --- Network & LAN Mobile Connectivity ---
  async fetchNetworkInfo() {
    try {
      const res = await fetch("/api/network");
      if (!res.ok) return;
      const data = await res.json();
      const mobileUrl = data.mobileUrl || `http://${window.location.hostname}:8000`;
      const badge = document.getElementById("lan-mobile-badge");
      const urlEl = document.getElementById("lan-mobile-url");
      if (badge) badge.style.display = "inline-flex";
      if (urlEl) urlEl.innerText = mobileUrl;
      this.mobileLanUrl = mobileUrl;
    } catch (e) {
      console.debug("Network info fetch skipped", e);
    }
  }

  copyMobileUrl() {
    const url = this.mobileLanUrl || window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      this.showToast(`Copied Mobile LAN URL: ${url}`, "success");
    }).catch(() => {
      this.showToast(`Mobile URL: ${url}`, "info");
    });
  }

  // --- Dev Bench Testing Runner ---
  async devTrigger(action) {
    try {
      this.showToast(`Bench Test: ${action}`, "info");
      const res = await fetch("/api/test/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      const log = document.getElementById("dev-console-log");
      if (log) {
        const time = new Date().toLocaleTimeString();
        log.innerHTML = `[${time}] ${action}: ${data.result || JSON.stringify(data)}<br>` + log.innerHTML;
      }
      if (data.event) {
        this.updateActiveAlertUI(data.event);
      }
    } catch (err) {
      console.error("Bench test error:", err);
      this.showToast(`Bench test failed: ${err.message}`, "error");
    }
  }

  // --- Toast Alert Notifications ---
  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = {
      success: "✅",
      error: "🚨",
      warning: "⚠️",
      info: "ℹ️"
    };

    toast.innerHTML = `
      <span style="font-size:1.1rem;">${icons[type] || 'ℹ️'}</span>
      <span style="flex:1;">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("toast-closing");
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 250);
    }, 3500);
  }
}

// Global instance
const app = new EchoSenseApp();
