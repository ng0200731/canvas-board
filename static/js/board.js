// board.js — Canvas board logic
(function () {
    "use strict";

    let cards = [];
    let connections = [];
    let lines = [];       // LeaderLine instances
    let draggables = [];  // PlainDraggable instances
    let viewMode = BOARD_VIEW_MODE;
    let connectMode = false;
    let connectFrom = null;
    let activeMenu = null;
    let activeCardId = null;
    let searchHighlight = [];

    const canvas = document.getElementById("canvas");
    const container = document.getElementById("canvas-container");
    const contextMenu = document.getElementById("card-context-menu");
    const fileInput = document.getElementById("file-upload-input");

    // ── API helpers ───────────────────────────────────────
    async function api(url, opts = {}) {
        const defaults = { headers: { "Content-Type": "application/json" } };
        if (opts.body && !(opts.body instanceof FormData)) {
            opts.body = JSON.stringify(opts.body);
        } else if (opts.body instanceof FormData) {
            delete defaults.headers["Content-Type"];
        }
        const res = await fetch(url, { ...defaults, ...opts });
        return res.json();
    }

    // ── Init ──────────────────────────────────────────────
    async function init() {
        const data = await api(`/api/boards/${BOARD_ID}/cards`);
        cards = data.cards;
        connections = data.connections;
        viewMode = data.view_mode;
        render();
        setupToolbar();
    }

    // ── Render ────────────────────────────────────────────
    function render() {
        cleanup();
        canvas.innerHTML = "";
        cards.forEach((card, i) => {
            const el = createCardEl(card, i);
            canvas.appendChild(el);
        });

        // Flowchart: position cards vertically with even spacing based on actual height
        if (viewMode === "flowchart") {
            const gap = 40;
            let top = 40;
            cards.forEach(card => {
                const el = document.getElementById(`card-${card.id}`);
                if (!el) return;
                el.style.top = top + "px";
                top += el.offsetHeight + gap;
            });
        }

        setupDrag();
        renderLines();
    }

    function cleanup() {
        lines.forEach(l => { try { l.remove(); } catch(e) {} });
        lines = [];
        draggables.forEach(d => { try { d.remove(); } catch(e) {} });
        draggables = [];
    }

    function createCardEl(card, index) {
        const el = document.createElement("div");
        el.className = "card";
        el.id = `card-${card.id}`;
        el.dataset.cardId = card.id;

        if (viewMode === "flowchart") {
            el.style.left = "400px";
            el.classList.add("no-drag");
        } else {
            el.style.left = (card.pos_x || 100) + "px";
            el.style.top = (card.pos_y || 100) + "px";
        }

        // Header
        const header = document.createElement("div");
        header.className = "card-header";
        const title = document.createElement("span");
        title.className = "card-title";
        title.contentEditable = "false";
        title.textContent = card.title;
        title.addEventListener("blur", () => {
            if (title.textContent !== card.title) {
                card.title = title.textContent;
                api(`/api/cards/${card.id}`, { method: "PATCH", body: { title: card.title } });
            }
            title.contentEditable = "false";
        });
        title.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); title.blur(); }
        });
        const menuBtn = document.createElement("button");
        menuBtn.className = "card-menu-btn";
        menuBtn.textContent = "...";
        menuBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            showContextMenu(e, card.id);
        });
        header.appendChild(title);
        header.appendChild(menuBtn);
        el.appendChild(header);

        // Files
        if (card.files && card.files.length > 0) {
            const filesDiv = document.createElement("div");
            filesDiv.className = "card-files";
            card.files.forEach(f => {
                if (f.is_image) {
                    const img = document.createElement("img");
                    img.src = f.thumb_url;
                    img.alt = f.original_name;
                    img.title = f.original_name;
                    img.addEventListener("click", () => window.open(f.url, "_blank"));
                    filesDiv.appendChild(img);
                } else {
                    const icon = document.createElement("div");
                    icon.className = "file-icon";
                    icon.textContent = f.original_name.split(".").pop().toUpperCase();
                    icon.title = f.original_name;
                    icon.addEventListener("click", () => window.open(f.url, "_blank"));
                    filesDiv.appendChild(icon);
                }
            });
            el.appendChild(filesDiv);
        }

        // Tags
        const tagsDiv = document.createElement("div");
        tagsDiv.className = "card-tags";
        (card.tags || []).forEach(t => {
            const tag = document.createElement("span");
            tag.className = "tag";
            tag.textContent = t.name;
            const rm = document.createElement("span");
            rm.className = "tag-remove";
            rm.textContent = "x";
            rm.addEventListener("click", async () => {
                await api(`/api/cards/${card.id}/tags/${t.id}`, { method: "DELETE" });
                card.tags = card.tags.filter(x => x.id !== t.id);
                tag.remove();
            });
            tag.appendChild(rm);
            tagsDiv.appendChild(tag);
        });
        const tagInput = document.createElement("input");
        tagInput.className = "tag-input";
        tagInput.placeholder = "+ tag";
        tagInput.addEventListener("keydown", async (e) => {
            if (e.key === "Enter" && tagInput.value.trim()) {
                e.preventDefault();
                const tagName = tagInput.value.trim();
                tagInput.value = "";
                const res = await api(`/api/cards/${card.id}/tags`, {
                    method: "POST", body: { name: tagName }
                });
                if (res.id) {
                    card.tags = card.tags || [];
                    card.tags.push(res);
                    render();
                }
            }
        });
        tagsDiv.appendChild(tagInput);
        el.appendChild(tagsDiv);

        // Drop zone for files
        const dropZone = document.createElement("div");
        dropZone.className = "card-drop-zone";
        dropZone.textContent = "Drop files here";
        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("drag-over");
        });
        dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
        dropZone.addEventListener("drop", async (e) => {
            e.preventDefault();
            dropZone.classList.remove("drag-over");
            const files = e.dataTransfer.files;
            if (files.length) await uploadFiles(card.id, card.board_id || BOARD_ID, files);
        });
        el.appendChild(dropZone);

        // Click for connect mode
        el.addEventListener("click", (e) => {
            if (connectMode && connectFrom && connectFrom !== card.id) {
                createConnection(connectFrom, card.id);
                connectMode = false;
                connectFrom = null;
                canvas.style.cursor = "default";
            }
        });

        return el;
    }

    // ── Drag ──────────────────────────────────────────────
    function setupDrag() {
        cards.forEach(card => {
            const el = document.getElementById(`card-${card.id}`);
            if (!el) return;
            try {
                const d = new PlainDraggable(el, {
                    handle: el,
                    onMove: () => { lines.forEach(l => { try { l.position(); } catch(e) {} }); },
                    onMoveEnd: () => {
                        const rect = el.getBoundingClientRect();
                        const containerRect = container.getBoundingClientRect();
                        const x = rect.left - containerRect.left + container.scrollLeft;
                        const y = rect.top - containerRect.top + container.scrollTop;
                        card.pos_x = x;
                        card.pos_y = y;
                        api(`/api/cards/${card.id}`, {
                            method: "PATCH",
                            body: { pos_x: x, pos_y: y }
                        });
                    }
                });

                // Prevent dragging when interacting with inputs
                el.querySelectorAll('input, [contenteditable="true"]').forEach(input => {
                    input.addEventListener('mousedown', (e) => e.stopPropagation());
                    input.addEventListener('touchstart', (e) => e.stopPropagation());
                });

                draggables.push(d);
            } catch(e) {
                console.warn("PlainDraggable init failed for card", card.id, e);
            }
        });
    }

    // ── Lines ─────────────────────────────────────────────
    function renderLines() {
        lines.forEach(l => { try { l.remove(); } catch(e) {} });
        lines = [];

        if (viewMode === "flowchart") {
            // Auto-connect sequential cards
            for (let i = 0; i < cards.length - 1; i++) {
                const fromEl = document.getElementById(`card-${cards[i].id}`);
                const toEl = document.getElementById(`card-${cards[i + 1].id}`);
                if (fromEl && toEl) {
                    try {
                        lines.push(new LeaderLine(fromEl, toEl, {
                            color: "#000",
                            size: 2,
                            path: "fluid",
                            startPlug: "disc",
                            endPlug: "arrow1",
                            startSocket: "bottom",
                            endSocket: "top",
                            dropShadow: false,
                            gradient: false
                        }));
                    } catch(e) {}
                }
            }
        }

        // User-created connections
        connections.forEach(conn => {
            const fromEl = document.getElementById(`card-${conn.from_card_id}`);
            const toEl = document.getElementById(`card-${conn.to_card_id}`);
            if (fromEl && toEl) {
                try {
                    const line = new LeaderLine(fromEl, toEl, {
                        color: "#000",
                        size: 2,
                        path: "fluid",
                        startPlug: "disc",
                        endPlug: "arrow1",
                        dropShadow: false,
                        gradient: false
                    });
                    line._connId = conn.id;
                    lines.push(line);
                } catch(e) {}
            }
        });
    }

    // ── Context menu ────────────────────────────────────────
    function showContextMenu(e, cardId) {
        activeCardId = cardId;
        contextMenu.style.display = "block";
        contextMenu.style.left = e.pageX + "px";
        contextMenu.style.top = e.pageY + "px";
    }

    document.addEventListener("click", () => {
        contextMenu.style.display = "none";
    });

    contextMenu.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", async () => {
            const action = btn.dataset.action;
            if (action === "delete-card") {
                await api(`/api/cards/${activeCardId}`, { method: "DELETE" });
                cards = cards.filter(c => c.id !== activeCardId);
                connections = connections.filter(c => c.from_card_id !== activeCardId && c.to_card_id !== activeCardId);
                render();
            } else if (action === "upload-file") {
                fileInput.dataset.cardId = activeCardId;
                fileInput.click();
            } else if (action === "edit-title") {
                const el = document.querySelector(`#card-${activeCardId} .card-title`);
                if (el) {
                    el.contentEditable = "true";
                    el.focus();
                    // Select all text
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }
        });
    });

    // ── File upload ───────────────────────────────────────
    fileInput.addEventListener("change", async () => {
        const cardId = fileInput.dataset.cardId;
        if (fileInput.files.length && cardId) {
            await uploadFiles(cardId, BOARD_ID, fileInput.files);
        }
        fileInput.value = "";
    });

    async function uploadFiles(cardId, boardId, fileList) {
        const fd = new FormData();
        for (const f of fileList) fd.append("files", f);
        const res = await fetch(`/api/cards/${cardId}/files`, { method: "POST", body: fd });
        const data = await res.json();
        if (data.files) {
            const card = cards.find(c => c.id === cardId);
            if (card) {
                card.files = card.files || [];
                card.files.push(...data.files);
                render();
            }
        }
    }

    // ── Connections ───────────────────────────────────────
    async function createConnection(fromId, toId) {
        const res = await api(`/api/boards/${BOARD_ID}/connections`, {
            method: "POST",
            body: { from_card_id: fromId, to_card_id: toId }
        });
        if (res.id) {
            connections.push(res);
            renderLines();
        }
    }

    // ── Toolbar ───────────────────────────────────────────
    function setupToolbar() {
        document.getElementById("btn-add-card").addEventListener("click", async () => {
            const scrollX = container.scrollLeft + 200;
            const scrollY = container.scrollTop + 100;
            const res = await api(`/api/boards/${BOARD_ID}/cards`, {
                method: "POST",
                body: { title: "New Card", pos_x: scrollX, pos_y: scrollY }
            });
            if (res.id) {
                cards.push(res);
                render();
            }
        });

        document.getElementById("btn-flowchart").addEventListener("click", () => {
            viewMode = "flowchart";
            document.getElementById("btn-flowchart").classList.add("active");
            document.getElementById("btn-freeform").classList.remove("active");
            api(`/boards/${BOARD_ID}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: `title=&view_mode=flowchart`
            });
            render();
        });

        document.getElementById("btn-freeform").addEventListener("click", () => {
            viewMode = "freeform";
            document.getElementById("btn-freeform").classList.add("active");
            document.getElementById("btn-flowchart").classList.remove("active");
            api(`/boards/${BOARD_ID}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: `title=&view_mode=freeform`
            });
            render();
        });

        // Search
        const searchInput = document.getElementById("search-input");
        let searchTimeout;
        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(async () => {
                const q = searchInput.value.trim();
                // Clear highlights
                document.querySelectorAll(".card").forEach(el => el.style.opacity = "1");
                if (!q) return;
                const res = await api(`/api/boards/${BOARD_ID}/search?q=${encodeURIComponent(q)}`);
                if (res.card_ids) {
                    document.querySelectorAll(".card").forEach(el => {
                        const cid = el.dataset.cardId;
                        el.style.opacity = res.card_ids.includes(cid) ? "1" : "0.2";
                    });
                }
            }, 300);
        });

        // Share
        document.getElementById("btn-share").addEventListener("click", () => {
            document.getElementById("share-modal").style.display = "flex";
        });
        document.getElementById("btn-close-share").addEventListener("click", () => {
            document.getElementById("share-modal").style.display = "none";
        });
        document.getElementById("btn-generate-link").addEventListener("click", async () => {
            const res = await api(`/boards/${BOARD_ID}/share`, { method: "POST" });
            if (res.url) {
                const fullUrl = window.location.origin + res.url;
                document.getElementById("share-link-input").value = fullUrl;
                document.getElementById("share-link-section").style.display = "block";
            }
        });
        document.getElementById("btn-copy-link").addEventListener("click", () => {
            const input = document.getElementById("share-link-input");
            input.select();
            navigator.clipboard.writeText(input.value);
        });
        document.getElementById("btn-send-email").addEventListener("click", async () => {
            const to = document.getElementById("send-email-to").value.trim();
            if (!to) return alert("Enter a recipient email.");
            const res = await api(`/boards/${BOARD_ID}/send`, {
                method: "POST", body: { to }
            });
            if (res.ok) alert("Email sent!");
            else alert("Error: " + (res.error || "Unknown"));
        });

        // Export
        document.getElementById("btn-export").addEventListener("click", async () => {
            window.open(`/boards/${BOARD_ID}/export`, "_blank");
        });
    }

    // ── Start ─────────────────────────────────────────────
    init();
})();
