(function () {
  const FINAL_STATES = new Set(["TERMINADA", "RETIRADA", "SUSPENDIDA"]);
  const RESPONDED_STATUSES = new Set(["CONFIRMADA", "RECHAZADA"]);
  let currentOrderId = "";
  let currentGeneratedLink = "";
  let latestConfirmationMap = {};

  function normalizeState(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, " ");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showNotice(message, tone) {
    if (typeof window.showToast === "function") {
      window.showToast(message, tone || "ok");
      return;
    }
    alert(message);
  }

  function injectStyles() {
    if (document.getElementById("confirmationRequestsStyles")) return;
    const style = document.createElement("style");
    style.id = "confirmationRequestsStyles";
    style.textContent = `
      .confirmation-cell{width:160px;text-align:center}
      .confirmation-row-btn,.confirmation-form-btn,.confirmation-modal button{
        border:none;border-radius:10px;padding:8px 12px;font:inherit;font-weight:700;cursor:pointer
      }
      .confirmation-row-btn,.confirmation-form-btn{background:#111;color:#fff;font-size:12px}
      .confirmation-row-btn[disabled],.confirmation-form-btn[disabled],.confirmation-modal button[disabled]{opacity:.5;cursor:not-allowed}
      .confirmation-modal{position:fixed;inset:0;z-index:70;background:rgba(0,0,0,.46);display:flex;align-items:center;justify-content:center;padding:18px}
      .confirmation-modal.is-hidden{display:none}
      .confirmation-modal-card{width:min(760px,100%);background:#fff;border-radius:20px;box-shadow:0 25px 60px rgba(0,0,0,.22);overflow:hidden}
      .confirmation-modal-head{display:flex;justify-content:space-between;gap:16px;padding:18px 20px;border-bottom:1px solid rgba(0,0,0,.08);background:linear-gradient(135deg,rgba(255,122,0,.16),rgba(255,255,255,.98))}
      .confirmation-modal-head strong{display:block;font-size:20px}
      .confirmation-modal-head span{display:block;font-size:13px;color:#555;margin-top:4px}
      .confirmation-modal-body{padding:20px;display:grid;gap:14px}
      .confirmation-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
      .confirmation-box{border:1px solid rgba(0,0,0,.1);border-radius:14px;padding:12px 13px;background:#fafafa}
      .confirmation-box strong{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#666;margin-bottom:5px}
      .confirmation-details{border:1px solid rgba(0,0,0,.1);border-radius:16px;padding:14px;background:#fffdf8}
      .confirmation-details-row{display:grid;grid-template-columns:140px 1fr;gap:10px;padding:6px 0;border-bottom:1px dashed rgba(0,0,0,.08)}
      .confirmation-details-row:last-child{border-bottom:none}
      .confirmation-details-row span:first-child{font-weight:700;color:#333}
      .confirmation-modal textarea,.confirmation-modal input{width:100%;border:1px solid rgba(0,0,0,.16);border-radius:12px;padding:10px 12px;font:inherit}
      .confirmation-modal-actions{display:flex;flex-wrap:wrap;gap:10px}
      .confirmation-modal .btn-primary{background:#ff7a00;color:#fff}
      .confirmation-modal .btn-dark{background:#121212;color:#fff}
      .confirmation-modal .btn-light{background:#eef2f7;color:#111}
      .confirmation-link-box{display:grid;gap:8px}
      .confirmation-link-box input{background:#f7f7f7}
      .confirmation-status{font-size:13px;color:#444}
      @media (max-width: 700px){
        .confirmation-details-row{grid-template-columns:1fr}
      }
    `;
    document.head.appendChild(style);
  }

  function ensureModal() {
    let modal = document.getElementById("confirmationModal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.id = "confirmationModal";
    modal.className = "confirmation-modal is-hidden";
    modal.innerHTML = `
      <div class="confirmation-modal-card">
        <div class="confirmation-modal-head">
          <div>
            <strong>Solicitar confirmacion</strong>
            <span>Genera un enlace publico para que el cliente confirme o rechace la reparacion.</span>
          </div>
          <button id="btnCloseConfirmationModal" type="button" class="btn-light">Cerrar</button>
        </div>
        <div class="confirmation-modal-body">
          <div id="confirmationModalSummary"></div>
          <label>
            <span>Mensaje opcional para el cliente</span>
            <textarea id="confirmationMessage" rows="3" placeholder="Ejemplo: por favor confirma si seguimos con el arreglo"></textarea>
          </label>
          <div class="confirmation-modal-actions">
            <button id="btnGenerateConfirmationLink" type="button" class="btn-primary">Generar link</button>
            <button id="btnSendConfirmationEmail" type="button" class="btn-dark">Generar y enviar mail</button>
            <button id="btnCopyConfirmationLink" type="button" class="btn-light" disabled>Copiar link</button>
          </div>
          <div class="confirmation-link-box">
            <input id="confirmationGeneratedLink" type="text" readonly placeholder="El enlace aparecera aca">
            <div id="confirmationLatestStatus" class="confirmation-status"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById("btnCloseConfirmationModal")?.addEventListener("click", closeModal);
    document.getElementById("btnGenerateConfirmationLink")?.addEventListener("click", () => createConfirmation(false));
    document.getElementById("btnSendConfirmationEmail")?.addEventListener("click", () => createConfirmation(true));
    document.getElementById("btnCopyConfirmationLink")?.addEventListener("click", async () => {
      if (!currentGeneratedLink) return;
      try {
        await navigator.clipboard.writeText(currentGeneratedLink);
        showNotice("Link copiado", "ok");
      } catch (_err) {
        showNotice("No se pudo copiar el link", "error");
      }
    });
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeModal();
    });
    return modal;
  }

  function openModal() {
    ensureModal().classList.remove("is-hidden");
  }

  function closeModal() {
    const modal = document.getElementById("confirmationModal");
    if (modal) modal.classList.add("is-hidden");
  }

  function setModalBusy(busy) {
    ["btnGenerateConfirmationLink", "btnSendConfirmationEmail", "btnCopyConfirmationLink"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (id === "btnCopyConfirmationLink" && !currentGeneratedLink) {
        el.disabled = true;
        return;
      }
      el.disabled = !!busy;
    });
  }

  function getCurrentOrderFromForm() {
    const id = String(document.getElementById("nro")?.value || "").trim();
    const state = normalizeState(document.getElementById("estado")?.value || "");
    return { id, state };
  }

  function ensureFormButton() {
    const bar = document.querySelector(".botonera-form");
    if (!bar) return null;
    let btn = document.getElementById("btnSolicitarConfirmacion");
    if (!btn) {
      btn = document.createElement("button");
      btn.id = "btnSolicitarConfirmacion";
      btn.type = "button";
      btn.className = "confirmation-form-btn is-hidden";
      btn.textContent = "Solicitar confirmacion";
      btn.addEventListener("click", async () => {
        const order = getCurrentOrderFromForm();
        if (!order.id) return;
        await loadConfirmationData(order.id);
        openModal();
      });
      bar.appendChild(btn);
    }
    return btn;
  }

  function syncFormButton() {
    const btn = ensureFormButton();
    if (!btn) return;
    const order = getCurrentOrderFromForm();
    const latest = latestConfirmationMap[order.id];
    const alreadyResponded = RESPONDED_STATUSES.has(String(latest?.decision_status || "").toUpperCase());
    const visible = !!order.id && !FINAL_STATES.has(order.state) && !alreadyResponded;
    btn.classList.toggle("is-hidden", !visible);
    btn.disabled = !visible;
  }

  function ensureHeaderCell() {
    const headRow = document.querySelector("#tablaOrdenes thead tr");
    if (!headRow) return;
    if (headRow.querySelector(".confirmation-header")) return;
    const th = document.createElement("th");
    th.className = "confirmation-header";
    th.textContent = "Confirmacion";
    headRow.appendChild(th);
  }

  function decorateOrderRows() {
    ensureHeaderCell();
    document.querySelectorAll("#tablaOrdenes tbody tr.orden-row").forEach((row) => {
      const existing = row.querySelector(".confirmation-cell");
      if (existing) existing.remove();

      const orderId = String(row.dataset.id || "").trim();
      const cells = row.querySelectorAll("td");
      const state = normalizeState(cells[7]?.textContent || "");
      const latest = latestConfirmationMap[orderId] || null;
      const alreadyResponded = RESPONDED_STATUSES.has(String(latest?.decision_status || "").toUpperCase());
      const cell = document.createElement("td");
      cell.className = "confirmation-cell";

      if (!FINAL_STATES.has(state) && !alreadyResponded) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "confirmation-row-btn";
        btn.textContent = "Solicitar";
        btn.addEventListener("click", async (event) => {
          event.preventDefault();
          event.stopPropagation();
          await loadConfirmationData(orderId);
          openModal();
        });
        cell.appendChild(btn);
      } else if (alreadyResponded) {
        cell.textContent = "Respondida";
      } else {
        cell.textContent = "-";
      }

      row.appendChild(cell);
    });

    document.querySelectorAll("#tablaOrdenes tbody tr.orden-detalle td[colspan]").forEach((cell) => {
      cell.setAttribute("colspan", "10");
    });
  }

  function latestStatusText(latestRequest) {
    if (!latestRequest) return "Todavia no se genero ninguna solicitud para esta orden.";
    const pieces = [
      `Ultima solicitud: ${latestRequest.decision_status || "PENDIENTE"}`,
      latestRequest.created_at ? `creada ${latestRequest.created_at}` : "",
      latestRequest.responded_at ? `respondida ${latestRequest.responded_at}` : "",
    ].filter(Boolean);
    return pieces.join(" | ");
  }

  function fillModalSummary(data) {
    const order = data.order || {};
    const latest = data.latest_request || null;
    currentGeneratedLink = latest?.public_url || "";
    const summary = document.getElementById("confirmationModalSummary");
    const linkInput = document.getElementById("confirmationGeneratedLink");
    const status = document.getElementById("confirmationLatestStatus");
    const copyBtn = document.getElementById("btnCopyConfirmationLink");
    const emailBtn = document.getElementById("btnSendConfirmationEmail");
    if (summary) {
      summary.innerHTML = `
        <div class="confirmation-grid">
          <div class="confirmation-box"><strong>Orden</strong>#${escapeHtml(order.id || "")}</div>
          <div class="confirmation-box"><strong>Estado</strong>${escapeHtml(order.estado || "-")}</div>
          <div class="confirmation-box"><strong>Cliente</strong>${escapeHtml(order.nombre_contacto || "-")}</div>
          <div class="confirmation-box"><strong>Email</strong>${escapeHtml(order.email_contacto || "-")}</div>
          <div class="confirmation-box"><strong>Telefono</strong>${escapeHtml(order.telefono_contacto || "-")}</div>
          <div class="confirmation-box"><strong>Sucursal</strong>${escapeHtml(order.sucursal_nombre || order.sucursal_key || "-")}</div>
        </div>
        <div class="confirmation-details">
          <div class="confirmation-details-row"><span>Equipo</span><span>${escapeHtml(order.equipo_texto || "-")}</span></div>
          <div class="confirmation-details-row"><span>Falla</span><span>${escapeHtml(order.falla || "-")}</span></div>
          <div class="confirmation-details-row"><span>Importe</span><span>${escapeHtml(order.importe || "-")}</span></div>
        </div>
      `;
    }
    if (linkInput) linkInput.value = currentGeneratedLink;
    if (status) status.textContent = latestStatusText(latest);
    if (copyBtn) copyBtn.disabled = !currentGeneratedLink;
    if (emailBtn) emailBtn.disabled = !data.smtp_configured || !String(order.email_contacto || "").trim();
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    let data = {};
    try {
      data = await response.json();
    } catch (_err) {
      data = {};
    }
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Error ${response.status}`);
    }
    return data;
  }

  async function refreshConfirmationStatuses() {
    const orderIds = Array.from(document.querySelectorAll("#tablaOrdenes tbody tr.orden-row"))
      .map((row) => String(row.dataset.id || "").trim())
      .filter(Boolean);
    if (!orderIds.length) {
      latestConfirmationMap = {};
      syncFormButton();
      return;
    }
    try {
      const data = await fetchJson(`/api/confirmaciones/estados?ids=${encodeURIComponent(orderIds.join(","))}`);
      latestConfirmationMap = data.items || {};
      decorateOrderRows();
      syncFormButton();
    } catch (_err) {
      // No rompemos la UI si este llamado falla.
    }
  }

  async function loadConfirmationData(orderId) {
    currentOrderId = String(orderId || "").trim();
    currentGeneratedLink = "";
    setModalBusy(true);
    try {
      const data = await fetchJson(`/api/confirmaciones/orden/${currentOrderId}`);
      fillModalSummary(data);
      openModal();
    } catch (err) {
      showNotice(err.message, "error");
    } finally {
      setModalBusy(false);
    }
  }

  async function createConfirmation(sendEmail) {
    if (!currentOrderId) return;
    const message = document.getElementById("confirmationMessage")?.value || "";
    setModalBusy(true);
    try {
      const data = await fetchJson(`/api/confirmaciones/orden/${currentOrderId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ send_email: !!sendEmail, message }),
      });
      fillModalSummary({
        order: data.order,
        latest_request: data.confirmation,
        smtp_configured: data.smtp_configured,
      });
      latestConfirmationMap[String(currentOrderId)] = {
        decision_status: data.confirmation?.decision_status || "PENDIENTE",
        responded_at: data.confirmation?.responded_at || null,
        created_at: data.confirmation?.created_at || null,
        id: data.confirmation?.id || null,
      };
      decorateOrderRows();
      syncFormButton();
      if (sendEmail && data.confirmation?.email_sent) {
        showNotice("Solicitud generada y enviada por mail", "ok");
      } else if (sendEmail && data.confirmation?.email_error) {
        showNotice(`Link generado, pero el mail fallo: ${data.confirmation.email_error}`, "error");
      } else {
        showNotice("Link generado correctamente", "ok");
      }
    } catch (err) {
      showNotice(err.message, "error");
    } finally {
      setModalBusy(false);
    }
  }

  function patchFunction(name, afterRun) {
    const original = window[name];
    if (typeof original !== "function" || original.__confirmationWrapped) return;
    const wrapped = function (...args) {
      const result = original.apply(this, args);
      Promise.resolve(result).finally(() => afterRun());
      return result;
    };
    wrapped.__confirmationWrapped = true;
    window[name] = wrapped;
  }

  function boot() {
    injectStyles();
    ensureModal();
    patchFunction("renderizarListaOrdenes", () => {
      decorateOrderRows();
      refreshConfirmationStatuses();
    });
    patchFunction("escribirFormulario", syncFormButton);
    patchFunction("limpiarFormularioOrden", syncFormButton);
    patchFunction("actualizarAccionesOrdenUI", syncFormButton);
    decorateOrderRows();
    refreshConfirmationStatuses();
    syncFormButton();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
