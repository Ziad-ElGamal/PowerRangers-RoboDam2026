(() => {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const backendHost = window.location.protocol === "file:"
        ? "127.0.0.1:8000"
        : window.location.host;
    const websocketUrl = protocol + backendHost + "/ws";
    let ws;
    let reconnectTimer;
    let reconnectDelay = 1000;
    let websocketConnected = false;
    let hubConnected = false;
    let lineChart, donutChart;
    let lastFeedSignature = "";
    let hasCredit = false;
    const nodeSlots = new Map();
    const slotNodeIds = [null, null, null, null];
    const pendingRelayStates = new Map();

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function statusClass(text) {
        const s = String(text || "").toLowerCase();
        if (s.includes("normal")) return "normal";
        if (s.includes("high") || s.includes("overload")) return "warning";
        if (s.includes("fault")) return "fault";
        return "offline";
    }

    function setConnected(on) {
        websocketConnected = on;
        if (!on) hubConnected = false;
        updateConnectionDisplay();
        syncRelayAvailability();
    }

    function setHubConnected(on) {
        hubConnected = on;
        updateConnectionDisplay();
        syncRelayAvailability();
    }

    function updateConnectionDisplay() {
        const el = document.getElementById("connection-status");
        if (el) {
            const fullyConnected = websocketConnected && hubConnected;
            el.textContent = fullyConnected
                ? "Connected"
                : websocketConnected ? "Hub Offline" : "Disconnected";
            el.className = "status " + (fullyConnected ? "connected" : "disconnected");
        }

        const feedStatus = document.querySelector(".offline-feed");
        if (feedStatus) {
            feedStatus.textContent = websocketConnected && hubConnected ? "Live Feed" : "Offline";
        }

        const analyticsStatus = document.querySelector(".analytics-status");
        if (analyticsStatus) {
            analyticsStatus.textContent = websocketConnected && hubConnected
                ? "Live"
                : "Waiting for Live Data";
        }
    }

    function renderFeed(items) {

        const feed = document.getElementById("ai-feed");
        if (!feed) return;

        const signature = JSON.stringify(items || []);
        if (signature === lastFeedSignature) return;
        lastFeedSignature = signature;

        feed.innerHTML = "";

        if (!items || items.length === 0) {
            feed.innerHTML = `
                <div class="alert-card alert-info">
                    <div>
                        <h3>No Active Alerts</h3>
                        <p>No recommendations or warnings are active right now.</p>
                    </div>
                </div>
            `;
            return;
        }

        items.forEach(item => {
            const level = item.level || "info";

            const cls =
                level === "warning" ? "alert-warning" :
                level === "success" ? "alert-success" :
                level === "danger" ? "alert-danger" :
                "alert-info";

            const title =
                level === "warning" ? "High Load Warning" :
                level === "success" ? "Energy Saving Tip" :
                level === "danger" ? "Emergency Alert" :
                "System Info";

            feed.insertAdjacentHTML(
                "beforeend",
                `<div class="alert-card ${cls}">
                    <div>
                        <h3>${title}</h3>
                        <p>${escapeHtml(item.msg)}</p>
                    </div>
                </div>`
            );
        });

        const moreHint = document.getElementById("feed-more-hint");

function updateMoreHint() {
    if (!moreHint) return;

    const hasMoreContent =
        feed.scrollHeight > feed.clientHeight + 5;

    const reachedBottom =
        feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 8;

    moreHint.style.display =
        hasMoreContent && !reachedBottom ? "block" : "none";
}

/* Wait until all recommendation cards are rendered */
requestAnimationFrame(updateMoreHint);

feed.onscroll = updateMoreHint;

    }

    const aiFeed = document.getElementById("ai-feed");
    const moreHint = document.getElementById("feed-more-hint");

    if (aiFeed && moreHint) {
        aiFeed.addEventListener("scroll", () => {
            const reachedBottom =
                aiFeed.scrollTop + aiFeed.clientHeight >= aiFeed.scrollHeight - 5;

            if (reachedBottom) {
                moreHint.style.display = "none";
                return;
            }

            const cards = aiFeed.querySelectorAll(".alert-card").length;
            moreHint.style.display = cards > 3 ? "block" : "none";
        });
    }

    function setRelayVisual(nodeNumber, isOn) {
        const relay = document.getElementById(`node${nodeNumber}-relay`);
        if (!relay) return;

        relay.textContent = isOn ? "ON" : "OFF";
        relay.className = `relay-button ${isOn ? "relay-on" : "relay-off"}`;
    }

    function setDeviceCutoffVisual(nodeNumber) {
        document.getElementById(`node${nodeNumber}-voltage`).textContent = "0.0 V";
        document.getElementById(`node${nodeNumber}-current`).textContent = "0.00 A";
        document.getElementById(`node${nodeNumber}-watts`).textContent = "0.0 W";

        const badge = document.getElementById(`node${nodeNumber}-status`);
        if (badge) {
            badge.textContent = "Offline";
            badge.className = "node-status offline";
        }
    }

    function syncRelayAvailability() {
        document.querySelectorAll(".relay-button").forEach((button) => {
            const commandPending = button.dataset.nodeId
                && pendingRelayStates.has(button.dataset.nodeId);
            const locked = !hasCredit || !websocketConnected || !hubConnected
                || !button.dataset.nodeId || commandPending;
            button.disabled = locked;
            button.setAttribute("aria-disabled", locked ? "true" : "false");
            button.style.cursor = locked ? "not-allowed" : "pointer";
            button.classList.toggle("credit-locked", locked);
        });
    }

    function slotForNode(nodeId) {
        if (nodeSlots.has(nodeId)) return nodeSlots.get(nodeId);

        const emptyIndex = slotNodeIds.findIndex(id => id === null);
        if (emptyIndex === -1) return null;

        const slot = emptyIndex + 1;
        slotNodeIds[emptyIndex] = nodeId;
        nodeSlots.set(nodeId, slot);
        return slot;
    }

    function markSlotOffline(slot) {
        const card = document.getElementById(`node${slot}-card`);
        if (card) card.hidden = true;

        document.getElementById(`node${slot}-voltage`).textContent = "0.0 V";
        document.getElementById(`node${slot}-current`).textContent = "0.00 A";
        document.getElementById(`node${slot}-watts`).textContent = "0.0 W";

        const badge = document.getElementById(`node${slot}-status`);
        badge.textContent = "Offline";
        badge.className = "node-status offline";

    }

    function updateEmptyNodesMessage() {
        const message = document.getElementById("no-connected-nodes");
        if (!message) return;
        message.hidden = slotNodeIds.some((nodeId, index) => {
            const card = document.getElementById(`node${index + 1}-card`);
            return nodeId && card && !card.hidden;
        });
    }

    function updateCharts(nodes) {
        if (typeof Chart === "undefined") return;

        const loadColors = ["#2ea8f2", "#ef476f", "#ff7a00", "#ffc928"];

        if (!lineChart) {
            lineChart = new Chart(document.getElementById("power-chart"), {
                type: "line",
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: { y: { beginAtZero: true } }
                }
            });

            document.getElementById("power-chart-container")
                ?.classList.add("chart-active");

            donutChart = new Chart(document.getElementById("load-chart"), {
                type: "doughnut",
                data: {
                    labels: nodes.map(n => n.name),
                    datasets: [{
                        data: nodes.map(n => Number(n.w)),
                        backgroundColor: loadColors,
                        borderColor: "#dbeafe",
                        borderWidth: 2,
                        hoverOffset: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    cutout: "55%",
                    radius: "88%",
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: context => {
                                    const values = context.dataset.data.map(Number);
                                    const total = values.reduce((sum, value) => sum + value, 0);
                                    const value = Number(context.raw || 0);
                                    const pct = total > 0 ? (value / total) * 100 : 0;
                                    return ` ${context.label}: ${value.toFixed(1)} W (${pct.toFixed(1)}%)`;
                                }
                            }
                        }
                    }
                }
            });

            document.getElementById("load-chart-container")
                ?.classList.add("chart-active");
        }

        nodes.forEach((node, index) => {
            let dataset = lineChart.data.datasets.find(d => d.nodeId === node.id);
            if (!dataset) {
                dataset = {
                    nodeId: node.id,
                    label: node.name,
                    data: Array(lineChart.data.labels.length).fill(null),
                    borderColor: loadColors[index % loadColors.length],
                    backgroundColor: loadColors[index % loadColors.length],
                    tension: 0.25
                };
                lineChart.data.datasets.push(dataset);
            }
            dataset.label = node.name;
        });

        lineChart.data.labels.push(new Date().toLocaleTimeString());

        const liveNodes = new Map(nodes.map(node => [node.id, node]));
        lineChart.data.datasets.forEach(dataset => {
            const node = liveNodes.get(dataset.nodeId);
            dataset.data.push(node ? Number(node.w) : null);
        });

        if (lineChart.data.labels.length > 60) {
            lineChart.data.labels.shift();
            lineChart.data.datasets.forEach(d => d.data.shift());
        }

        lineChart.update("none");

        const watts = nodes.map(n => Number(n.w));
        const total = watts.reduce((sum, value) => sum + value, 0);

        donutChart.data.labels = nodes.map(n => n.name);
        donutChart.data.datasets[0].data = watts;
        donutChart.data.datasets[0].backgroundColor = loadColors;
        donutChart.update("none");

        const breakdown = document.getElementById("load-breakdown");
        if (breakdown) {
            breakdown.innerHTML = nodes.map((n, i) => {
                const value = Number(n.w);
                const pct = total > 0 ? (value / total) * 100 : 0;
                return `
                    <div class="load-breakdown-row">
                        <div class="load-device">
                            <span class="load-dot" style="background:${loadColors[i % loadColors.length]}"></span>
                            <span class="load-device-name">${escapeHtml(n.name)}</span>
                        </div>
                        <span class="load-value">${value.toFixed(1)} W (${pct.toFixed(1)}%)</span>
                    </div>
                `;
            }).join("");
        }
    }

    function handleMessage(event) {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (error) {
            console.error("Invalid WebSocket message", error);
            return;
        }

        if (data.type === "hub_status") {
            setHubConnected(Boolean(data.connected));
            slotNodeIds.forEach((nodeId, index) => {
                if (nodeId) markSlotOffline(index + 1);
            });
            updateEmptyNodesMessage();
            return;
        }

        if (data.type === "relay_ack") {
            const pending = pendingRelayStates.get(data.node_id);
            if (!pending) return;

            if (!data.ok) {
                setRelayVisual(pending.slot, pending.previousState);
                console.error(data.message || "Relay command failed");
            }
            pendingRelayStates.delete(data.node_id);
            syncRelayAvailability();
            return;
        }

        if (data.type === "rename_ack") {
            const slot = nodeSlots.get(String(data.node_id));
            if (!data.ok) {
                const editButton = slot
                    && document.querySelector(`.node-name-edit[data-slot="${slot}"]`);
                if (editButton) delete editButton.dataset.pendingName;
                window.alert(data.message || "Could not rename this node");
                return;
            }

            const nameElement = slot && document.getElementById(`node${slot}-name`);
            if (nameElement) nameElement.textContent = data.name;
            if (slot) {
                localStorage.removeItem(`robodam-slot-name-${slot}`);
                const editButton = document.querySelector(`.node-name-edit[data-slot="${slot}"]`);
                if (editButton) delete editButton.dataset.pendingName;
            }
            return;
        }

        if (data.type === "balance_ack") {
            if (!data.ok) {
                window.alert(data.message || "Could not add balance");
                return;
            }

            hasCredit = Number(data.balance) > 0;
            document.getElementById("prepaid-balance").textContent =
                `${Number(data.balance).toFixed(2)} EGP`;
            syncRelayAvailability();
            return;
        }

        if (!Array.isArray(data.nodes)) return;
        setHubConnected(data.hub_connected !== false);

        // Relay buttons stay enabled while credit is available.
        // When credit reaches zero, every relay becomes disabled.
        hasCredit = Number(data.prepaid_balance) > 0;

        syncRelayAvailability();


        document.getElementById("prepaid-balance").textContent =
            `${Number(data.prepaid_balance).toFixed(2)} EGP`;

        const tariffInfo = document.getElementById("tariff-info");
        if (tariffInfo) {
            tariffInfo.textContent =
                `Third tier: ${Number(data.tariff_egp_per_kwh || 0.95).toFixed(2)} EGP/kWh` +
                ` • ${Number(data.monthly_energy_kwh || 0).toFixed(4)} kWh this month`;
        }

        const predicted = Number(data.predicted_hours_left || 0);

        if (predicted > 0) {
        const totalHours = Math.floor(predicted);

        const days = Math.floor(totalHours / 24);
        const hours = totalHours % 24;

        document.getElementById("predicted-time").textContent =
            `${days} Days , ${hours} Hours`;
        } else {
        document.getElementById("predicted-time").textContent = "--";
        }

        let total = 0;

        const connectedNodeIds = new Set(data.nodes.map(node => String(node.id)));
        slotNodeIds.forEach((nodeId, index) => {
            if (!nodeId) return;

            markSlotOffline(index + 1);
            if (!connectedNodeIds.has(nodeId)) {
                nodeSlots.delete(nodeId);
                slotNodeIds[index] = null;
                const editButton = document.querySelector(
                    `.node-name-edit[data-slot="${index + 1}"]`
                );
                if (editButton) delete editButton.dataset.nodeId;
            }
        });

        data.nodes.forEach(node => {
            const n = slotForNode(String(node.id));
            if (!n) return;
            const card = document.getElementById(`node${n}-card`);
            if (card) card.hidden = false;
            total += Number(node.w);

            const nameElement = document.getElementById(`node${n}-name`);
            const pendingSlotName = localStorage.getItem(`robodam-slot-name-${n}`);
            if (nameElement) nameElement.textContent = pendingSlotName || node.name;

            document.getElementById(`node${n}-voltage`).textContent =
                `${Number(node.v).toFixed(1)} V`;
            document.getElementById(`node${n}-current`).textContent =
                `${Number(node.a).toFixed(2)} A`;
            document.getElementById(`node${n}-watts`).textContent =
                `${Number(node.w).toFixed(1)} W`;

            const badge = document.getElementById(`node${n}-status`);
            badge.textContent = node.status;
            badge.className = `node-status ${statusClass(node.status)}`;

            const relayButton = document.getElementById(`node${n}-relay`);
            relayButton.dataset.nodeId = String(node.id);
            const pendingRelay = pendingRelayStates.get(String(node.id));
            setRelayVisual(
                n,
                pendingRelay ? pendingRelay.requestedState : Boolean(node.relay_on)
            );

            const editButton = document.querySelector(`.node-name-edit[data-slot="${n}"]`);
            if (editButton) {
                editButton.dataset.nodeId = String(node.id);
                editButton.disabled = false;

                if (
                    pendingSlotName
                    && editButton.dataset.pendingName !== pendingSlotName
                    && ws?.readyState === WebSocket.OPEN
                ) {
                    editButton.dataset.pendingName = pendingSlotName;
                    ws.send(JSON.stringify({
                        type: "rename_node",
                        node_id: String(node.id),
                        name: pendingSlotName
                    }));
                }
            }
        });

        updateEmptyNodesMessage();

        // Re-apply the credit lock after relay visuals are rendered.
        syncRelayAvailability();

        document.getElementById("total-load").textContent =
        `${total.toFixed(1)} W`;

        renderFeed(data.ai_recommendations || []);
        updateCharts(data.nodes);
    }

    function connectWebSocket() {
        clearTimeout(reconnectTimer);
        ws = new WebSocket(websocketUrl);

        ws.onopen = () => {
            reconnectDelay = 1000;
            setConnected(true);
        };
        ws.onmessage = handleMessage;
        ws.onerror = () => ws.close();
        ws.onclose = () => {
            setConnected(false);
            reconnectTimer = setTimeout(connectWebSocket, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, 10000);
        };
    }

    document.querySelectorAll(".relay-button").forEach(btn => {
        btn.addEventListener("click", () => {
            if (!ws || ws.readyState !== WebSocket.OPEN) return;
            if (!hasCredit || btn.disabled || btn.getAttribute("aria-disabled") === "true") return;

            const nodeNumber = Number(btn.id.match(/\d+/)?.[0]);
            const nodeId = btn.dataset.nodeId;
            if (!nodeNumber || !nodeId) return;

            const previousState = btn.textContent.trim() === "ON";
            const turnOn = btn.textContent.trim() !== "ON";
            pendingRelayStates.set(nodeId, {
                slot: nodeNumber,
                previousState,
                requestedState: turnOn
            });
            syncRelayAvailability();

            // Optimistic UI: react instantly.
            setRelayVisual(nodeNumber, turnOn);

            if (!turnOn) {
                setDeviceCutoffVisual(nodeNumber);
            }

            ws.send(JSON.stringify({
                type: "relay",
                node_id: nodeId,
                relay_on: turnOn
            }));
        });
    });

    document.querySelectorAll(".node-name-edit").forEach(button => {
        button.addEventListener("click", () => {
            const slot = Number(button.dataset.slot);
            const nodeId = button.dataset.nodeId;
            const nameElement = document.getElementById(`node${slot}-name`);
            if (!slot || !nameElement) return;

            const requestedName = window.prompt(
                "Enter a name for this appliance (maximum 32 characters):",
                nameElement.textContent.trim()
            );
            if (requestedName === null) return;

            const cleanName = requestedName.trim();
            if (!cleanName || cleanName.length > 32) {
                window.alert("Use a name between 1 and 32 characters.");
                return;
            }

            nameElement.textContent = cleanName;

            if (!nodeId || !ws || ws.readyState !== WebSocket.OPEN) {
                localStorage.setItem(`robodam-slot-name-${slot}`, cleanName);
                return;
            }

            ws.send(JSON.stringify({
                type: "rename_node",
                node_id: nodeId,
                name: cleanName
            }));
        });
    });

    for (let slot = 1; slot <= 4; slot += 1) {
        const savedSlotName = localStorage.getItem(`robodam-slot-name-${slot}`);
        const nameElement = document.getElementById(`node${slot}-name`);
        if (savedSlotName && nameElement) nameElement.textContent = savedSlotName;
    }

    document.getElementById("add-balance-button")?.addEventListener("click", () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            window.alert("The dashboard server is disconnected.");
            return;
        }

        const requestedAmount = window.prompt("Enter the amount to add in EGP:", "50.00");
        if (requestedAmount === null) return;

        const amount = Number(requestedAmount);
        if (!Number.isFinite(amount) || amount <= 0) {
            window.alert("Enter an amount greater than 0 EGP.");
            return;
        }

        ws.send(JSON.stringify({type: "add_balance", amount}));
    });

    setConnected(false);
    connectWebSocket();
})();
