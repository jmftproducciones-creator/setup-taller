import json
import os
import secrets
import smtplib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from email.message import EmailMessage
from urllib.parse import quote

import mysql.connector
from flask import Blueprint, current_app, jsonify, render_template, request, url_for


FINAL_CONFIRMATION_STATES = {"TERMINADA", "RETIRADA", "SUSPENDIDA"}


def get_confirmation_table_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS solicitudes_confirmacion (
        id INT AUTO_INCREMENT PRIMARY KEY,
        token VARCHAR(120) NOT NULL,
        orden_id INT NOT NULL,
        sucursal_key VARCHAR(50) NOT NULL,
        order_status_snapshot VARCHAR(80) NULL,
        customer_name VARCHAR(255) NULL,
        customer_email VARCHAR(255) NULL,
        customer_phone VARCHAR(80) NULL,
        requested_by VARCHAR(120) NULL,
        requested_by_name VARCHAR(120) NULL,
        message_text TEXT NULL,
        snapshot_json LONGTEXT NULL,
        decision_status VARCHAR(40) NOT NULL DEFAULT 'PENDIENTE',
        decision_note TEXT NULL,
        responder_name VARCHAR(120) NULL,
        responded_at DATETIME NULL,
        expires_at DATETIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_solicitudes_confirmacion_token (token),
        KEY idx_solicitudes_confirmacion_orden (sucursal_key, orden_id),
        KEY idx_solicitudes_confirmacion_status (decision_status),
        KEY idx_solicitudes_confirmacion_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """


def register_confirmation_module(
    app,
    *,
    branches,
    shared_db_name,
    build_db_config,
    get_db,
    shared_table,
    login_required,
    insert_hist,
    to_upper,
):
    bp = Blueprint("confirmaciones", __name__)
    table_ready = {"done": False}
    column_cache = {}

    def shared_db():
        return mysql.connector.connect(**build_db_config(shared_db_name))

    def ensure_confirmation_table():
        if table_ready["done"]:
            return
        conn = shared_db()
        cur = conn.cursor()
        cur.execute(get_confirmation_table_sql())
        conn.commit()
        cur.close()
        conn.close()
        table_ready["done"] = True

    def table_columns(table_name):
        if table_name in column_cache:
            return column_cache[table_name]
        conn = shared_db()
        cur = conn.cursor()
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        cols = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        column_cache[table_name] = cols
        return cols

    def serialize_value(value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            sign = "-" if total_seconds < 0 else ""
            total_seconds = abs(total_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if seconds:
                return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
            return f"{sign}{hours:02d}:{minutes:02d}"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, time):
            return value.strftime("%H:%M")
        return value

    def serialize_row(row):
        if not row:
            return {}
        return {key: serialize_value(value) for key, value in row.items()}

    def smtp_is_configured():
        return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))

    def normalize_decision(raw):
        value = str(raw or "").strip().lower()
        if value in {"confirmar", "confirmado", "aprobar", "aprobada", "aceptar", "aceptado"}:
            return "CONFIRMADA"
        if value in {"rechazar", "rechazado", "rechazada", "denegar", "negada", "negar"}:
            return "RECHAZADA"
        return ""

    def build_share_payload(public_url, order):
        customer_name = order.get("nombre_contacto") or "cliente"
        subject = f"Confirmacion de orden #{order['id']}"
        body = (
            f"Hola {customer_name},\n\n"
            f"Te compartimos el enlace para confirmar si queres continuar con la reparacion "
            f"de la orden #{order['id']}.\n\n{public_url}\n\n"
            "Si preferis, tambien podes responder por este mismo medio."
        )
        return {
            "public_url": public_url,
            "mailto_url": f"mailto:{quote(order.get('email_contacto') or '')}"
            f"?subject={quote(subject)}&body={quote(body)}",
            "share_text": body,
            "customer_email": order.get("email_contacto") or "",
            "customer_phone": order.get("telefono_contacto") or "",
        }

    def send_confirmation_email(to_email, public_url, order, extra_message=""):
        host = os.getenv("SMTP_HOST", "").strip()
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USER", "").strip()
        password = os.getenv("SMTP_PASSWORD", "").strip()
        from_email = os.getenv("SMTP_FROM", "").strip()
        use_tls = os.getenv("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "si", "s"}
        use_ssl = os.getenv("SMTP_USE_SSL", "0").strip().lower() in {"1", "true", "yes", "si", "s"}

        if not host or not from_email:
            raise RuntimeError("SMTP no configurado")

        customer_name = order.get("nombre_contacto") or "cliente"
        subject = f"Confirmacion de reparacion - orden #{order['id']}"
        body_lines = [
            f"Hola {customer_name},",
            "",
            "Te compartimos el enlace para confirmar si queres continuar con la reparacion:",
            public_url,
            "",
        ]
        if extra_message:
            body_lines.extend([extra_message.strip(), ""])
        body_lines.extend(
            [
                f"Equipo: {order.get('equipo_texto') or '-'}",
                f"Falla: {order.get('falla') or '-'}",
                f"Importe estimado: {order.get('importe') or '-'}",
            ]
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email
        message.set_content("\n".join(body_lines))

        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
        try:
            server.ehlo()
            if use_tls and not use_ssl:
                server.starttls()
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(message)
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def fetch_order_snapshot(order_id, branch_key):
        client_cols = table_columns("clientes")
        email_expr = "c.email AS email_contacto" if "email" in client_cols else "NULL AS email_contacto"
        phone_candidates = []
        if "telefono" in client_cols:
            phone_candidates.append("NULLIF(TRIM(c.telefono),'')")
        if "celular" in client_cols:
            phone_candidates.append("NULLIF(TRIM(c.celular),'')")
        phone_expr = f"COALESCE({', '.join(phone_candidates)}, '') AS telefono_contacto" if phone_candidates else "'' AS telefono_contacto"

        conn = get_db(branch_key)
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                o.*,
                c.nombre AS nombre_contacto,
                """
            + email_expr
            + """,
                """
            + phone_expr
            + """,
                e.serie AS serie_texto,
                CONCAT_WS(' ', e.descripcion, e.marca, e.modelo) AS equipo_texto
            FROM ordenes o
            LEFT JOIN """
            + shared_table("clientes")
            + """ c ON c.id = o.cliente_id
            LEFT JOIN """
            + shared_table("equipos")
            + """ e ON e.id = o.equipo_id
            WHERE o.id=%s
            LIMIT 1
            """,
            (order_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        row["sucursal_nombre"] = branches.get(branch_key, {}).get("name", branch_key)
        return serialize_row(row)

    def fetch_latest_request(order_id, branch_key):
        ensure_confirmation_table()
        conn = shared_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT *
            FROM solicitudes_confirmacion
            WHERE orden_id=%s AND sucursal_key=%s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (order_id, branch_key),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        row = serialize_row(row)
        row["snapshot"] = {}
        if row.get("snapshot_json"):
            try:
                row["snapshot"] = json.loads(row["snapshot_json"])
            except Exception:
                row["snapshot"] = {}
        row["public_url"] = url_for("confirmaciones.confirmation_public", token=row["token"], _external=True)
        row["share"] = build_share_payload(row["public_url"], row["snapshot"] or {"id": order_id})
        return row

    def fetch_latest_requests_map(order_ids, branch_key):
        ensure_confirmation_table()
        ids = [int(item) for item in order_ids if str(item).isdigit()]
        if not ids:
            return {}
        placeholders = ", ".join(["%s"] * len(ids))
        conn = shared_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""
            SELECT sc.*
            FROM solicitudes_confirmacion sc
            INNER JOIN (
                SELECT orden_id, sucursal_key, MAX(id) AS max_id
                FROM solicitudes_confirmacion
                WHERE sucursal_key=%s AND orden_id IN ({placeholders})
                GROUP BY orden_id, sucursal_key
            ) latest
                ON latest.max_id = sc.id
            """,
            tuple([branch_key] + ids),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        result = {}
        for row in rows:
            clean = serialize_row(row)
            result[str(clean["orden_id"])] = {
                "decision_status": clean.get("decision_status") or "PENDIENTE",
                "responded_at": clean.get("responded_at"),
                "created_at": clean.get("created_at"),
                "id": clean.get("id"),
            }
        return result

    def mark_old_requests_replaced(order_id, branch_key):
        ensure_confirmation_table()
        conn = shared_db()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE solicitudes_confirmacion
            SET decision_status='REEMPLAZADA'
            WHERE orden_id=%s AND sucursal_key=%s AND decision_status='PENDIENTE'
            """,
            (order_id, branch_key),
        )
        conn.commit()
        cur.close()
        conn.close()

    def create_request(order_id, branch_key, requested_by, requested_by_name, send_email=False, message_text=""):
        order = fetch_order_snapshot(order_id, branch_key)
        if not order:
            raise ValueError("Orden no encontrada")
        if to_upper(order.get("estado")) in FINAL_CONFIRMATION_STATES:
            raise ValueError("Solo se puede solicitar confirmacion en ordenes no finalizadas")

        mark_old_requests_replaced(order_id, branch_key)

        token = secrets.token_urlsafe(24)
        expires_at = datetime.now() + timedelta(days=10)
        ensure_confirmation_table()
        conn = shared_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO solicitudes_confirmacion (
                token, orden_id, sucursal_key, order_status_snapshot,
                customer_name, customer_email, customer_phone,
                requested_by, requested_by_name, message_text,
                snapshot_json, decision_status, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE', %s)
            """,
            (
                token,
                order_id,
                branch_key,
                order.get("estado"),
                order.get("nombre_contacto"),
                order.get("email_contacto"),
                order.get("telefono_contacto"),
                requested_by,
                requested_by_name,
                message_text.strip() or None,
                json.dumps(order, ensure_ascii=False),
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        request_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()

        public_url = url_for("confirmaciones.confirmation_public", token=token, _external=True)
        email_sent = False
        email_error = ""
        if send_email:
            if not order.get("email_contacto"):
                email_error = "El cliente no tiene email cargado"
            else:
                try:
                    send_confirmation_email(order["email_contacto"], public_url, order, message_text)
                    email_sent = True
                except Exception as exc:
                    email_error = str(exc)

        payload = fetch_latest_request(order_id, branch_key) or {}
        payload.update(
            {
                "id": request_id,
                "token": token,
                "public_url": public_url,
                "share": build_share_payload(public_url, order),
                "email_sent": email_sent,
                "email_error": email_error,
            }
        )
        return order, payload

    def insert_customer_history(branch_key, order_id, action, note):
        conn = get_db(branch_key)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orden_historial (orden_id, usuario, accion, nota)
            VALUES (%s, %s, %s, %s)
            """,
            (order_id, "cliente", action, note),
        )
        conn.commit()
        cur.close()
        conn.close()

    @bp.route("/api/confirmaciones/orden/<int:orden_id>", methods=["GET"])
    @login_required
    def confirmation_order_detail(orden_id):
        from flask import session

        branch_key = session.get("branch_key")
        order = fetch_order_snapshot(orden_id, branch_key)
        if not order:
            return jsonify({"ok": False, "error": "Orden no encontrada"}), 404
        return jsonify(
            {
                "ok": True,
                "order": order,
                "latest_request": fetch_latest_request(orden_id, branch_key),
                "smtp_configured": smtp_is_configured(),
                "final_states": sorted(FINAL_CONFIRMATION_STATES),
            }
        )

    @bp.route("/api/confirmaciones/orden/<int:orden_id>", methods=["POST"])
    @login_required
    def confirmation_order_create(orden_id):
        from flask import session

        branch_key = session.get("branch_key")
        data = request.get_json(silent=True) or {}
        send_email = bool(data.get("send_email"))
        message_text = str(data.get("message") or "")
        try:
            order, confirmation = create_request(
                orden_id,
                branch_key,
                requested_by=session.get("username") or "sistema",
                requested_by_name=session.get("display_name") or session.get("username") or "Sistema",
                send_email=send_email,
                message_text=message_text,
            )
            hist_conn = get_db(branch_key)
            try:
                insert_hist(hist_conn, orden_id, "REQUEST_CONFIRMATION", message_text or "Solicitud enviada")
            finally:
                hist_conn.close()
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:
            current_app.logger.exception("Error creando solicitud de confirmacion")
            return jsonify({"ok": False, "error": str(exc)}), 500

        return jsonify(
            {
                "ok": True,
                "order": order,
                "confirmation": confirmation,
                "smtp_configured": smtp_is_configured(),
            }
        )

    @bp.route("/api/confirmaciones/estados", methods=["GET"])
    @login_required
    def confirmation_statuses():
        from flask import session

        raw_ids = str(request.args.get("ids") or "")
        order_ids = [chunk.strip() for chunk in raw_ids.split(",") if chunk.strip()]
        branch_key = session.get("branch_key")
        return jsonify({"ok": True, "items": fetch_latest_requests_map(order_ids, branch_key)})

    @bp.route("/confirmacion/<token>", methods=["GET"])
    def confirmation_public(token):
        ensure_confirmation_table()
        conn = shared_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT *
            FROM solicitudes_confirmacion
            WHERE token=%s
            LIMIT 1
            """,
            (token,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return render_template("confirmacion_publica.html", request_data=None, order=None, status="INVALIDA")

        row = serialize_row(row)
        snapshot = {}
        if row.get("snapshot_json"):
            try:
                snapshot = json.loads(row["snapshot_json"])
            except Exception:
                snapshot = {}

        status = row.get("decision_status") or "PENDIENTE"
        if row.get("expires_at"):
            try:
                if status == "PENDIENTE" and datetime.fromisoformat(row["expires_at"]) < datetime.now():
                    status = "VENCIDA"
            except Exception:
                pass

        return render_template(
            "confirmacion_publica.html",
            request_data=row,
            order=snapshot,
            status=status,
        )

    @bp.route("/confirmacion/<token>/resolver", methods=["POST"])
    def confirmation_public_resolve(token):
        payload = request.get_json(silent=True) or {}
        decision = normalize_decision(payload.get("decision"))
        responder_name = str(payload.get("responder_name") or "").strip()
        note = str(payload.get("note") or "").strip()
        if not decision:
            return jsonify({"ok": False, "error": "Decision invalida"}), 400

        ensure_confirmation_table()
        conn = shared_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT *
            FROM solicitudes_confirmacion
            WHERE token=%s
            LIMIT 1
            """,
            (token,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Solicitud no encontrada"}), 404

        row = serialize_row(row)
        current_status = row.get("decision_status") or "PENDIENTE"
        if current_status != "PENDIENTE":
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": f"Esta solicitud ya fue {current_status.lower()}"}), 400

        if row.get("expires_at"):
            try:
                if datetime.fromisoformat(row["expires_at"]) < datetime.now():
                    cur.close()
                    conn.close()
                    return jsonify({"ok": False, "error": "La solicitud ya vencio"}), 400
            except Exception:
                pass

        branch_key = row["sucursal_key"]
        order_id = row["orden_id"]
        branch_conn = get_db(branch_key)
        branch_cur = branch_conn.cursor(dictionary=True)
        branch_cur.execute("SELECT id, estado FROM ordenes WHERE id=%s LIMIT 1", (order_id,))
        order_row = branch_cur.fetchone()
        if not order_row:
            branch_cur.close()
            branch_conn.close()
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "La orden ya no existe"}), 404

        order_state = to_upper(order_row.get("estado"))
        if order_state in FINAL_CONFIRMATION_STATES:
            branch_cur.close()
            branch_conn.close()
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "La orden ya no admite confirmacion"}), 400

        branch_update = branch_conn.cursor()
        if decision == "CONFIRMADA":
            branch_update.execute(
                "UPDATE ordenes SET presupuesto_aprobado=1 WHERE id=%s",
                (order_id,),
            )
            branch_note = note or "Cliente confirma continuar con la reparacion"
            customer_action = "CUSTOMER_CONFIRMED"
        else:
            branch_update.execute(
                "UPDATE ordenes SET presupuesto_aprobado=0, estado='SUSPENDIDA' WHERE id=%s",
                (order_id,),
            )
            branch_note = note or "Cliente rechaza continuar con la reparacion"
            customer_action = "CUSTOMER_REJECTED"
        branch_conn.commit()
        branch_update.close()
        branch_cur.close()
        branch_conn.close()

        update_cur = conn.cursor()
        update_cur.execute(
            """
            UPDATE solicitudes_confirmacion
            SET decision_status=%s,
                decision_note=%s,
                responder_name=%s,
                responded_at=NOW()
            WHERE token=%s
            """,
            (decision, branch_note, responder_name or None, token),
        )
        conn.commit()
        update_cur.close()
        cur.close()
        conn.close()

        insert_customer_history(branch_key, order_id, customer_action, branch_note)

        return jsonify(
            {
                "ok": True,
                "decision_status": decision,
                "message": "La respuesta fue registrada correctamente",
            }
        )

    app.register_blueprint(bp)
