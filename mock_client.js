(() => {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const ws = new WebSocket(protocol + window.location.host + "/ws");
    let lineChart, donutChart;
    let lastFeedSignature = "";
    let hasCredit = false;

    function statusClass(text) {
        const s = String(text || "").toLowerCase();
        if (s.includes("normal")) return "normal";
        if (s.includes("high") || s.includes("overload")) return "warning";
        if (s.includes("fault")) return "fault";
        return "offline";
    }

    function setConnected(on) {
        const el = document.getElementById("connection-status");
        if (el) {
            el.textContent = on ? "Connected" : "Disconnected";
            el.className = "status " + (on ? "connected" : "disconnected");
        }

        const feedStatus = document.querySelector(".offline-feed");
        if (feedStatus) {
            feedStatus.textContent = on ? "Live Feed" : "Offline";
        }

        const analyticsStatus = document.querySelector(".analytics-status");
        if (analyticsStatus) {
            analyticsStatus.textContent = on ? "Live" : "Waiting for Live Data";
        }

        document.querySelectorAll(".relay-button").forEach(btn => {
            btn.disabled = !on || !hasCredit;
        });
        
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
                        <p>${item.msg}</p>
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
            const locked = !hasCredit;
            button.disabled = locked;
            button.setAttribute("aria-disabled", locked ? "true" : "false");
            button.style.cursor = locked ? "not-allowed" : "pointer";
            button.classList.toggle("credit-locked", locked);
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
                    datasets: nodes.map(n => ({
                        label: n.name,
                        data: [],
                        tension: 0.25
                    }))
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

        lineChart.data.labels.push(new Date().toLocaleTimeString());

        nodes.forEach((n, i) => {
            lineChart.data.datasets[i].data.push(Number(n.w));
        });

        if (lineChart.data.labels.length > 30) {
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
                            <span class="load-device-name">${n.name}</span>
                        </div>
                        <span class="load-value">${value.toFixed(1)} W (${pct.toFixed(1)}%)</span>
                    </div>
                `;
            }).join("");
        }
    }

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = event => {
        const data = JSON.parse(event.data);

        // Relay buttons stay enabled while credit is available.
        // When credit reaches zero, every relay becomes disabled.
        hasCredit = Number(data.prepaid_balance) > 0;

        syncRelayAvailability();


        document.getElementById("prepaid-balance").textContent =
            `${Number(data.prepaid_balance).toFixed(2)} EGP`;

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

        data.nodes.forEach((node, index) => {
            const n = index + 1;
            total += Number(node.w);

            const nameElement = document.getElementById(`node${n}-name`);
            if (nameElement) {
                nameElement.textContent = node.name;
            }

            document.getElementById(`node${n}-voltage`).textContent =
                `${Number(node.v).toFixed(1)} V`;
            document.getElementById(`node${n}-current`).textContent =
                `${Number(node.a).toFixed(2)} A`;
            document.getElementById(`node${n}-watts`).textContent =
                `${Number(node.w).toFixed(1)} W`;

            const badge = document.getElementById(`node${n}-status`);
            badge.textContent = node.status;
            badge.className = `node-status ${statusClass(node.status)}`;

            setRelayVisual(n, Boolean(node.relay_on));
        });

        // Re-apply the credit lock after relay visuals are rendered.
        syncRelayAvailability();

        document.getElementById("total-load").textContent =
        `${total.toFixed(1)} W`;

        renderFeed(data.ai_recommendations || []);
        updateCharts(data.nodes);
    };

    document.querySelectorAll(".relay-button").forEach(btn => {
        btn.addEventListener("click", () => {
            if (ws.readyState !== WebSocket.OPEN) return;
            if (!hasCredit || btn.disabled || btn.getAttribute("aria-disabled") === "true") return;

            const nodeNumber = Number(btn.id.match(/\d+/)?.[0]);
            if (!nodeNumber) return;

            const turnOn = btn.textContent.trim() !== "ON";

            // Optimistic UI: react instantly.
            setRelayVisual(nodeNumber, turnOn);

            if (!turnOn) {
                setDeviceCutoffVisual(nodeNumber);
            }

            ws.send(JSON.stringify({
                type: "relay",
                node_id: `node_${nodeNumber}`,
                relay_on: turnOn
            }));
        });
    });

    setConnected(false);
})();