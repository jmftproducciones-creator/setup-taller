import os
from functools import wraps
from datetime import datetime, date, time, timedelta

import mysql.connector
from mysql.connector import Error
from mysql.connector.errors import IntegrityError

from flask import Flask, render_template, request, jsonify, session, send_from_directory
import subprocess
from orden_docx import generar_docx_orden
import re
import unicodedata
from werkzeug.security import check_password_hash, generate_password_hash

def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file(os.path.join(os.path.dirname(__file__), ".env"))

DOCX_DIR = os.path.join(os.path.dirname(__file__), "docx_ordenes")
os.makedirs(DOCX_DIR, exist_ok=True)

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "si", "s")

# En VPS/Linux conviene dejar esto apagado. En Windows local podes activar con
# ABRIR_WORD_AL_CREAR=1 o ABRIR_WORD_AL_MODIFICAR=1.
ABRIR_WORD_AL_CREAR = env_bool("ABRIR_WORD_AL_CREAR", False)
ABRIR_WORD_AL_MODIFICAR = env_bool("ABRIR_WORD_AL_MODIFICAR", False)

def abrir_archivo_windows(path: str):
    if os.name != "nt":
        return
    try:
        os.startfile(path)  # âœ… Windows
    except Exception as e:
        print("WARN abrir_archivo_windows:", e)


def generar_word_de_orden(conn, orden_id: int, abrir: bool = False) -> str:
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            o.*,
            c.nombre   AS nombre_contacto,
            COALESCE(NULLIF(TRIM(c.telefono),''), NULLIF(TRIM(c.celular),''), '') AS telefono_contacto,
            e.serie    AS serie_texto,
            CONCAT_WS(' ', e.descripcion, e.marca, e.modelo) AS equipo_texto
        FROM ordenes o
        LEFT JOIN """ + shared_table("clientes") + """ c ON c.id = o.cliente_id
        LEFT JOIN """ + shared_table("equipos") + """ e ON e.id = o.equipo_id
        WHERE o.id=%s
        LIMIT 1
    """, (orden_id,))
    orden = cur.fetchone()
    cur.close()

    if not orden:
        raise RuntimeError("Orden no encontrada para generar Word")

    path = generar_docx_orden(orden, output_dir=DOCX_DIR)

    if abrir:
        abrir_archivo_windows(path)

    return path

ESTADOS_EN_PROCESO = {
    "EN REPARACION", "EN SOS", "EN WERTECH", "EN EKON",
    "EN AIR", "EN SERVIPRINT", "EN NICO GORI"
}
ESTADO_TERMINADA = "TERMINADA"
ESTADO_RETIRADA  = "RETIRADA"

def to_upper(s):
    return str(s or "").strip().upper()

def to_capitalize(s):
    """
    Normaliza texto:
    - strip
    - colapsa espacios
    - capitalize por oraciÃ³n simple (primera letra mayus, resto igual)
    Si querÃ©s TODO uppercase para textos tambiÃ©n, te lo cambio.
    """
    if s is None:
        return None
    t = str(s).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return None
    return t[:1].upper() + t[1:]

def parse_fecha(v):
    # espera YYYY-MM-DD
    if not v:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v[:10]

def parse_hora(v):
    # espera HH:MM
    if not v:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v[:5]

def now_fecha_hora():
    # usÃ¡ tu funciÃ³n existente si ya la tenÃ©s
    from datetime import datetime
    d = datetime.now()
    return d.strftime("%Y-%m-%d"), d.strftime("%H:%M")

def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # sin tildes
    s = re.sub(r"\s+", " ", s)
    return s

def clean_digits(s: str) -> str:
    return re.sub(r"\D", "", _clean_text(s))

def clean_email(s: str) -> str:
    return _clean_text(s).lower()

def clean_serie(s: str) -> str:
    # Serie/SN: mayÃºsculas y sin espacios
    return re.sub(r"\s+", "", to_upper(s))

# ========= APP =========
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "cambiar-esta-secret-key")

# ========= CONFIGURACION DB / SUCURSALES =========
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_PORT = int(os.getenv('DB_PORT', '3306'))

BRANCHES = {
    "central": {
        "key": "central",
        "name": os.getenv("BRANCH_CENTRAL_NAME", "Sucursal Verde"),
        "database": os.getenv("DB_NAME_CENTRAL", os.getenv("DB_NAME", "setup")),
        "theme": "central",
    },
    "naranja": {
        "key": "naranja",
        "name": os.getenv("BRANCH_NARANJA_NAME", "Sucursal Naranja"),
        "database": os.getenv("DB_NAME_NARANJA", "setup_naranja"),
        "theme": "naranja",
    },
}
SHARED_DB_NAME = BRANCHES["central"]["database"]


def build_db_config(database_name: str) -> dict:
    return {
        'host': DB_HOST,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'database': database_name,
        'port': DB_PORT,
    }

if env_bool("AUTO_INIT_DB", False):
    try:
        import init_db
        init_db.main()
    except Exception as e:
        print("WARN init_db:", e)

def _auth_db():
    return mysql.connector.connect(**build_db_config(SHARED_DB_NAME))


def get_shared_db():
    return mysql.connector.connect(**build_db_config(SHARED_DB_NAME))


def shared_table(name: str) -> str:
    return f"`{SHARED_DB_NAME}`.`{name}`"


def get_branch_config(branch_key: str | None = None) -> dict:
    branch = BRANCHES.get(branch_key or session.get("branch_key"))
    if branch:
        return branch
    return BRANCHES["central"]


def get_db(branch_key: str | None = None):
    branch = get_branch_config(branch_key)
    return mysql.connector.connect(**build_db_config(branch["database"]))




def _usuario_actual():
    return session.get("username", request.headers.get("X-User", "sistema"))

def _insert_hist(conn, orden_id, accion, nota=None):
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orden_historial (orden_id, usuario, accion, nota)
            VALUES (%s, %s, %s, %s)
            """,
            (orden_id, _usuario_actual(), accion, nota),
        )
        cur.close()
    except Exception:
        pass

def normalize_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        # fechas / datetimes
        if isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        # horas puras
        elif isinstance(v, time):
            out[k] = v.strftime("%H:%M:%S")
        # campos TIME de MySQL que vienen como timedelta
        elif isinstance(v, timedelta):
            total = int(v.total_seconds())
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            out[k] = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            out[k] = v
    return out


def _public_branches():
    return [
        {
            "key": branch["key"],
            "name": branch["name"],
            "theme": branch["theme"],
        }
        for branch in BRANCHES.values()
    ]


def branch_name(branch_key: str | None) -> str:
    branch = BRANCHES.get(branch_key or "")
    return branch["name"] if branch else (branch_key or "")


def _get_user_with_branches(username: str):
    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, username, password_hash, display_name, email, telefono, activo, is_admin
        FROM usuarios
        WHERE username=%s
        LIMIT 1
        """,
        (username,),
    )
    user = cur.fetchone()
    if user:
        cur.execute(
            """
            SELECT sucursal_key
            FROM usuario_sucursal
            WHERE usuario_id=%s
            ORDER BY sucursal_key
            """,
            (user["id"],),
        )
        user["branches"] = [row["sucursal_key"] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return user


def _current_user_row():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, username, display_name, email, telefono, activo, is_admin
        FROM usuarios
        WHERE id=%s
        LIMIT 1
        """,
        (user_id,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def _session_payload() -> dict:
    branch_key = session.get("branch_key")
    branch = BRANCHES.get(branch_key)
    available_keys = session.get("allowed_branches", [])
    available_branches = [BRANCHES[key] for key in available_keys if key in BRANCHES]
    return {
        "authenticated": bool(session.get("user_id")),
        "username": session.get("username"),
        "display_name": session.get("display_name"),
        "is_admin": bool(session.get("is_admin")),
        "branch": {
            "key": branch["key"],
            "name": branch["name"],
            "theme": branch["theme"],
        } if branch else None,
        "allowed_branches": [
            {
                "key": item["key"],
                "name": item["name"],
                "theme": item["theme"],
            }
            for item in available_branches
        ],
        "available_branches": _public_branches(),
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "Sesion no iniciada"}), 401
        branch_key = session.get("branch_key")
        allowed = session.get("allowed_branches", [])
        if not branch_key or branch_key not in allowed or branch_key not in BRANCHES:
            return jsonify({"ok": False, "error": "Sucursal no habilitada"}), 403
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "Sesion no iniciada"}), 401
        if not bool(session.get("is_admin")):
            return jsonify({"ok": False, "error": "Solo un administrador puede realizar esta acción"}), 403
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def protect_api_routes():
    if not request.path.startswith("/api/"):
        return None
    public_paths = {"/api/login", "/api/session"}
    if request.path in public_paths:
        return None
    if request.path.startswith("/static/"):
        return None
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Sesion no iniciada"}), 401
    branch_key = session.get("branch_key")
    allowed = session.get("allowed_branches", [])
    if not branch_key or branch_key not in allowed or branch_key not in BRANCHES:
        return jsonify({"ok": False, "error": "Sucursal no habilitada"}), 403
    return None


# ========= PÃGINAS PRINCIPALES =========
@app.route("/")
def index():
    return render_template("ordenes.html", app_context=_session_payload())


@app.route("/ordenes")
def ordenes():
    return render_template("ordenes.html", app_context=_session_payload())


@app.route("/api/session", methods=["GET"])
def api_session():
    return jsonify(_session_payload())


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    branch_key = str(data.get("branch_key") or "").strip()

    if not username or not password or not branch_key:
        return jsonify({"ok": False, "error": "Usuario, contraseña y sucursal son obligatorios"}), 400

    user = _get_user_with_branches(username)
    if not user or not int(user.get("activo") or 0):
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401
    if branch_key not in user.get("branches", []):
        return jsonify({"ok": False, "error": "El usuario no tiene acceso a esa sucursal"}), 403

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["display_name"] = user.get("display_name") or user["username"]
    session["is_admin"] = 1 if int(user.get("is_admin") or 0) == 1 else 0
    session["allowed_branches"] = user["branches"]
    session["branch_key"] = branch_key

    return jsonify({"ok": True, "session": _session_payload()})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/switch-branch", methods=["POST"])
def api_switch_branch():
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Sesion no iniciada"}), 401

    data = request.get_json(silent=True) or {}
    branch_key = str(data.get("branch_key") or "").strip()
    allowed = session.get("allowed_branches", [])

    if branch_key not in allowed or branch_key not in BRANCHES:
        return jsonify({"ok": False, "error": "Sucursal no habilitada"}), 403

    session["branch_key"] = branch_key
    return jsonify({"ok": True, "session": _session_payload()})


@app.route("/api/me", methods=["GET"])
def api_me():
    user = _current_user_row()
    if not user:
        return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404
    user["branches"] = session.get("allowed_branches", [])
    user["active_branch"] = session.get("branch_key")
    user["is_admin"] = bool(int(user.get("is_admin") or 0))
    return jsonify({"ok": True, "user": user})


@app.route("/api/me", methods=["PUT"])
def api_me_update():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "Sesion no iniciada"}), 401

    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    display_name = str(data.get("display_name") or "").strip()
    email = str(data.get("email") or "").strip()
    telefono = str(data.get("telefono") or "").strip()
    new_password = str(data.get("password") or "")

    if not username or not display_name:
        return jsonify({"ok": False, "error": "Usuario y nombre a mostrar son obligatorios"}), 400

    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM usuarios WHERE username=%s AND id<>%s LIMIT 1", (username, user_id))
    exists = cur.fetchone()
    if exists:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Ese nombre de usuario ya está en uso"}), 409

    params = [username, display_name, email or None, telefono or None, user_id]
    sql = """
        UPDATE usuarios
        SET username=%s,
            display_name=%s,
            email=%s,
            telefono=%s
    """
    if new_password.strip():
        sql += ", password_hash=%s"
        params.insert(4, generate_password_hash(new_password.strip()))
    sql += " WHERE id=%s"

    cur2 = conn.cursor()
    cur2.execute(sql, tuple(params))
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()

    session["username"] = username
    session["display_name"] = display_name
    return jsonify({"ok": True, "session": _session_payload()})


@app.route("/api/usuarios", methods=["GET"])
@admin_required
def api_usuarios():
    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, username, display_name, email, telefono, activo, is_admin
        FROM usuarios
        ORDER BY display_name, username
        """
    )
    users = cur.fetchall()

    cur.execute(
        """
        SELECT usuario_id, sucursal_key
        FROM usuario_sucursal
        ORDER BY usuario_id, sucursal_key
        """
    )
    rows = cur.fetchall()
    branches_by_user = {}
    for row in rows:
        branches_by_user.setdefault(row["usuario_id"], []).append(row["sucursal_key"])

    for user in users:
        user["branches"] = branches_by_user.get(user["id"], [])
        user["is_admin"] = bool(int(user.get("is_admin") or 0))
        user["activo"] = bool(int(user.get("activo") or 0))

    cur.close()
    conn.close()
    return jsonify({"ok": True, "users": users, "branches": _public_branches()})


@app.route("/api/usuarios", methods=["POST"])
@admin_required
def api_usuarios_crear():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    display_name = str(data.get("display_name") or "").strip()
    email = str(data.get("email") or "").strip()
    telefono = str(data.get("telefono") or "").strip()
    password = str(data.get("password") or "").strip()
    branches = [b for b in (data.get("branches") or []) if b in BRANCHES]
    is_admin = 1 if int(data.get("is_admin") or 0) == 1 else 0
    activo = 1 if int(data.get("activo") or 0) == 1 else 0

    if not username or not display_name or not password:
        return jsonify({"ok": False, "error": "Usuario, nombre y contraseña son obligatorios"}), 400
    if not branches:
        return jsonify({"ok": False, "error": "Debés asignar al menos una sucursal"}), 400

    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM usuarios WHERE username=%s LIMIT 1", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Ese nombre de usuario ya existe"}), 409

    cur2 = conn.cursor()
    cur2.execute(
        """
        INSERT INTO usuarios (username, display_name, email, telefono, password_hash, activo, is_admin)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            username,
            display_name,
            email or None,
            telefono or None,
            generate_password_hash(password),
            activo,
            is_admin,
        ),
    )
    user_id = cur2.lastrowid
    for branch_key in branches:
        cur2.execute(
            """
            INSERT INTO usuario_sucursal (usuario_id, sucursal_key)
            VALUES (%s, %s)
            """,
            (user_id, branch_key),
        )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()
    return jsonify({"ok": True, "id": user_id})


@app.route("/api/usuarios/<int:user_id>", methods=["PUT"])
@admin_required
def api_usuarios_actualizar(user_id: int):
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    display_name = str(data.get("display_name") or "").strip()
    email = str(data.get("email") or "").strip()
    telefono = str(data.get("telefono") or "").strip()
    password = str(data.get("password") or "").strip()
    branches = [b for b in (data.get("branches") or []) if b in BRANCHES]
    is_admin = 1 if int(data.get("is_admin") or 0) == 1 else 0
    activo = 1 if int(data.get("activo") or 0) == 1 else 0

    if not username or not display_name:
        return jsonify({"ok": False, "error": "Usuario y nombre son obligatorios"}), 400
    if not branches:
        return jsonify({"ok": False, "error": "Debés asignar al menos una sucursal"}), 400

    conn = _auth_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM usuarios WHERE id=%s LIMIT 1", (user_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404

    cur.execute("SELECT id FROM usuarios WHERE username=%s AND id<>%s LIMIT 1", (username, user_id))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Ese nombre de usuario ya existe"}), 409

    params = [username, display_name, email or None, telefono or None, activo, is_admin]
    sql = """
        UPDATE usuarios
        SET username=%s,
            display_name=%s,
            email=%s,
            telefono=%s,
            activo=%s,
            is_admin=%s
    """
    if password:
        sql += ", password_hash=%s"
        params.append(generate_password_hash(password))
    sql += " WHERE id=%s"
    params.append(user_id)

    cur2 = conn.cursor()
    cur2.execute(sql, tuple(params))
    cur2.execute("DELETE FROM usuario_sucursal WHERE usuario_id=%s", (user_id,))
    for branch_key in branches:
        cur2.execute(
            """
            INSERT INTO usuario_sucursal (usuario_id, sucursal_key)
            VALUES (%s, %s)
            """,
            (user_id, branch_key),
        )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()

    if session.get("user_id") == user_id:
        session["username"] = username
        session["display_name"] = display_name
        session["is_admin"] = is_admin
        session["allowed_branches"] = branches
        if session.get("branch_key") not in branches:
            session["branch_key"] = branches[0]

    return jsonify({"ok": True, "session": _session_payload()})


# ========= API CATÃLOGOS SENCILLOS (fallas / reparaciones / repuestos / accesorios) =========
@app.route("/api/fallas", methods=["GET"])
def api_fallas():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, descripcion FROM fallas ORDER BY descripcion")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/api/reparaciones", methods=["GET"])
def api_reparaciones():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, descripcion FROM reparaciones ORDER BY descripcion")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/api/repuestos", methods=["GET"])
def api_repuestos():
    """Lista de repuestos (incluye costo para que el front pueda sumar)."""
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, nombre, descripcion, costo
        FROM repuestos
        ORDER BY nombre
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # normalizo por si algÃºn dÃ­a costo es DECIMAL, etc.
    return jsonify([normalize_row(r) for r in rows])


@app.route("/api/accesorios", methods=["GET"])
def api_accesorios():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nombre FROM accesorios ORDER BY nombre")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@app.route("/api/clientes", methods=["GET"])
def api_clientes():
    conn = get_shared_db()
    cur = conn.cursor(dictionary=True)

    # SELECT * para no romper si agregÃ¡s/quitÃ¡s columnas
    cur.execute("SELECT * FROM clientes ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    rows = [normalize_row(r) for r in rows]
    return jsonify(rows)

def _clientes_tiene_col(conn, colname: str) -> bool:
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'clientes'
          AND COLUMN_NAME = %s
    """, (colname,))
    ok = (cur.fetchone() or {}).get("c", 0) > 0
    cur.close()
    return ok
@app.route("/api/clientes", methods=["POST"])
def api_clientes_crear():
    data = request.json or {}

    nombre   = to_capitalize(data.get("nombre"))

    telefono = clean_digits(data.get("telefono")) or None

    if not nombre:
        return jsonify({"ok": False, "error": "El nombre del cliente es obligatorio"}), 400

    conn = get_shared_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            """
            SELECT id
            FROM clientes
            WHERE nombre=%s
              AND (telefono=%s OR (telefono IS NULL AND %s IS NULL))
            """,
            (nombre, telefono, telefono),
        )
        existente = cur.fetchone()
        if existente:
            cur.close(); conn.close()
            return jsonify({
                "ok": False,
                "error": "Ya existe un cliente con ese nombre y telÃ©fono",
                "id": existente["id"],
            }), 409

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clientes
              (nombre, direccion, localidad, provincia, cp,
               telefono, email, cuit, contacto,
               observaciones, giro_empresa,
               cliente_garantia, cliente_con_contrato)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                nombre,
                to_capitalize(data.get("direccion")) or None,
                to_capitalize(data.get("localidad")) or None,
                to_capitalize(data.get("provincia")) or None,
                _clean_text(data.get("cp")) or None,
                telefono,
                clean_email(data.get("email")),
                clean_digits(data.get("cuit")) or None,
                to_capitalize(data.get("contacto")) or None,
                to_capitalize(data.get("observaciones")) or None,
                to_capitalize(data.get("giro_empresa")) or None,
                data.get("cliente_garantia") or 0,
                data.get("cliente_con_contrato") or 0,
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.close(); conn.close()
        return jsonify({"ok": True, "id": new_id})

    except Error as e:
        print("Error api_clientes_crear:", e)

        if getattr(e, "errno", None) == 1062:
            return jsonify({"ok": False, "error": "Cliente duplicado (restricciÃ³n Ãºnica)"}), 409

        conn.rollback()
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Error al guardar cliente"}), 500
@app.route("/api/clientes/<int:cliente_id>", methods=["PUT"])
def api_clientes_actualizar(cliente_id):
    data = request.json or {}

    nombre   = to_capitalize(data.get("nombre"))

    telefono = clean_digits(data.get("telefono")) or None

    if not nombre:
        return jsonify({"ok": False, "error": "El nombre del cliente es obligatorio"}), 400

    conn = get_shared_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            """
            SELECT id
            FROM clientes
            WHERE nombre=%s
              AND (telefono=%s OR (telefono IS NULL AND %s IS NULL))
              AND id <> %s
            """,
            (nombre, telefono, telefono, cliente_id),
        )
        duplicado = cur.fetchone()
        if duplicado:
            cur.close(); conn.close()
            return jsonify({
                "ok": False,
                "error": "Ya existe otro cliente con ese nombre y telÃ©fono",
                "id": duplicado["id"],
            }), 409

        cur = conn.cursor()
        cur.execute(
            """
            UPDATE clientes
            SET nombre=%s,
                direccion=%s,
                localidad=%s,
                provincia=%s,
                cp=%s,
                telefono=%s,
                email=%s,
                cuit=%s,
                contacto=%s,
                observaciones=%s,
                giro_empresa=%s,
                cliente_garantia=%s,
                cliente_con_contrato=%s
            WHERE id=%s
            """,
            (
                nombre,
                to_capitalize(data.get("direccion")) or None,
                to_capitalize(data.get("localidad")) or None,
                to_capitalize(data.get("provincia")) or None,
                _clean_text(data.get("cp")) or None,
                telefono,
                clean_email(data.get("email")),
                clean_digits(data.get("cuit")) or None,
                to_capitalize(data.get("contacto")) or None,
                to_capitalize(data.get("observaciones")) or None,
                to_capitalize(data.get("giro_empresa")) or None,
                data.get("cliente_garantia") or 0,
                data.get("cliente_con_contrato") or 0,
                cliente_id,
            ),
        )
        conn.commit()
        cur.close(); conn.close()
        return jsonify({"ok": True})

    except Error as e:
        print("Error api_clientes_actualizar:", e)
        conn.rollback()
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Error al actualizar cliente"}), 500


# ========= API EQUIPOS (siempre ligados a un cliente) =========
@app.route("/api/equipos", methods=["GET"])
def api_equipos():
    """
    Devuelve los equipos junto con:
    - cliente_id (cliente principal propietario)
    - clientes (string con todos los clientes asociados, separador ", ")
    """
    conn = get_shared_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT
            e.*,
            MIN(CASE WHEN ec.activo = 1 THEN ec.cliente_id END) AS cliente_id,
            GROUP_CONCAT(c.nombre SEPARATOR ', ') AS clientes
        FROM equipos e
        LEFT JOIN equipo_cliente ec
               ON e.id = ec.equipo_id AND ec.activo = 1
        LEFT JOIN clientes c
               ON ec.cliente_id = c.id
        GROUP BY e.id
        ORDER BY e.id DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([normalize_row(r) for r in rows])


@app.route("/api/equipos", methods=["POST"])
def crear_equipo_api():
    data = request.json or {}

    descripcion = to_capitalize(data.get("descripcion"))
    serie_raw  = data.get("serie")
    serie      = clean_serie(serie_raw)
    serie_norm = serie


    cliente_id  = data.get("cliente_id")

    if not descripcion and not serie:
        return jsonify({"ok": False, "error": "Debe indicar al menos DescripciÃ³n o Serie"}), 400
    if not cliente_id:
        return jsonify({"ok": False, "error": "Debe seleccionar un cliente para el equipo"}), 400

    try:
        conn = get_shared_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO equipos (descripcion, serie, serie_norm, tipo, marca, modelo)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                descripcion or None,
                serie or None,
                serie_norm or None,
                to_capitalize(data.get("tipo")) or None,
                to_capitalize(data.get("marca")) or None,
                to_capitalize(data.get("modelo")) or None,
            ),
        )

        conn.commit()
        equipo_id = cur.lastrowid
        cur.close()

        # vincular con cliente
        vincular_equipo_cliente(conn, equipo_id, int(cliente_id), "propietario")

        conn.close()
        return jsonify({"ok": True, "id": equipo_id})

    except Error as e:
        print("Error crear_equipo:", e)

        # 1062 = Duplicate entry (ej: serie Ãºnica)
        if getattr(e, "errno", None) == 1062:
            return jsonify({
                "ok": False,
                "error": "Ya existe un equipo con esa SERIE. ElegÃ­ otra o buscÃ¡ el equipo existente."
            }), 409

        # 1452 = FK fail
        if getattr(e, "errno", None) == 1452:
            return jsonify({
                "ok": False,
                "error": "Cliente invÃ¡lido (no existe). SeleccionÃ¡ un cliente vÃ¡lido."
            }), 409

        return jsonify({"ok": False, "error": "Error al guardar equipo"}), 500
@app.route("/api/equipos/<int:equipo_id>", methods=["PUT"])
def modificar_equipo_api(equipo_id):
    data = request.json or {}

    descripcion = to_capitalize(data.get("descripcion"))
    serie       = clean_serie(data.get("serie"))
    cliente_id  = data.get("cliente_id")

    if not descripcion and not serie:
        return jsonify({"ok": False, "error": "Debe indicar al menos DescripciÃ³n o Serie"}), 400
    if not cliente_id:
        return jsonify({"ok": False, "error": "Debe seleccionar un cliente para el equipo"}), 400

    try:
        conn = get_shared_db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE equipos
            SET descripcion=%s, serie=%s, tipo=%s, marca=%s, modelo=%s
            WHERE id=%s
            """,
            (
                descripcion or None,
                serie or None,
                to_capitalize(data.get("tipo")) or None,
                to_capitalize(data.get("marca")) or None,
                to_capitalize(data.get("modelo")) or None,
                equipo_id,
            ),
        )
        conn.commit()
        cur.close()

        vincular_equipo_cliente(conn, equipo_id, int(cliente_id), "propietario")

        conn.close()
        return jsonify({"ok": True})

    except Error as e:
        print("Error modificar_equipo:", e)

        if getattr(e, "errno", None) == 1062:
            return jsonify({
                "ok": False,
                "error": "No se pudo guardar: la SERIE ya existe en otro equipo."
            }), 409

        return jsonify({"ok": False, "error": "Error al modificar equipo"}), 500

def vincular_equipo_cliente(conn, equipo_id, cliente_id, rol="propietario"):
    """
    Mantiene la tabla equipo_cliente con tu esquema actual:
      (equipo_id, cliente_id, rol, fecha_asignacion, activo)

    - Desactiva vÃ­nculos activos del equipo
    - Reactiva o inserta el vÃ­nculo con el cliente
    """
    cur = conn.cursor()

    # 1) desactivar todas las relaciones activas de ese equipo
    cur.execute(
        "UPDATE equipo_cliente SET activo=0 WHERE equipo_id=%s AND activo=1",
        (equipo_id,),
    )

    # 2) ver si ya existe vÃ­nculo equipo-cliente
    cur.execute(
        """
        SELECT id
        FROM equipo_cliente
        WHERE equipo_id=%s AND cliente_id=%s
        """,
        (equipo_id, cliente_id),
    )
    row = cur.fetchone()

    if row:
        # reactivar y actualizar rol
        cur.execute(
            """
            UPDATE equipo_cliente
            SET activo=1, rol=%s
            WHERE id=%s
            """,
            (rol, row[0]),
        )
    else:
        # crear nuevo vÃ­nculo
        cur.execute(
            """
            INSERT INTO equipo_cliente (equipo_id, cliente_id, rol, activo)
            VALUES (%s, %s, %s, 1)
            """,
            (equipo_id, cliente_id, rol),
        )

    conn.commit()
    cur.close()

# ========= API Ã“RDENES =========

def buscar_o_crear_cliente(conn, nombre, telefono):
    """
    Busca un cliente por nombre y telÃ©fono. Si no existe, lo crea.
    Devuelve el id del cliente.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id FROM clientes
        WHERE nombre=%s AND (telefono=%s OR (telefono IS NULL AND %s IS NULL))
        """,
        (nombre, telefono, telefono),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0]

    cur.execute(
        "INSERT INTO clientes (nombre, telefono) VALUES (%s, %s)",
        (nombre, telefono),
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id
@app.route("/api/ordenes", methods=["GET"])
def api_ordenes():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            o.*,
            c.nombre   AS nombre_contacto,
            COALESCE(NULLIF(TRIM(c.telefono),''), NULLIF(TRIM(c.celular),''), '') AS telefono_contacto,
            e.serie    AS serie_texto,
            CONCAT_WS(' ', e.descripcion, e.marca, e.modelo) AS equipo_texto
        FROM ordenes o
        LEFT JOIN """ + shared_table("clientes") + """ c ON c.id = o.cliente_id
        LEFT JOIN """ + shared_table("equipos") + """ e ON e.id = o.equipo_id
        ORDER BY o.id DESC
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    rows = [normalize_row(r) for r in rows]
    for row in rows:
        row["sucursal_nombre"] = branch_name(row.get("sucursal_key"))
    return jsonify(rows)



def normalizar_orden(data: dict) -> dict:
    data["estado"] = to_upper(data.get("estado"))

    data["telefono_contacto"] = re.sub(
        r"\D", "", data.get("telefono_contacto") or ""
    )

    for campo in (
        "observaciones",
        "accesorios",
        "falla",
        "reparacion",
        "repuestos",
    ):
        data[campo] = to_capitalize(data.get(campo))

    return data


@app.route("/api/fallas", methods=["POST"])
def api_crear_falla():
    data = request.get_json()
    desc = to_capitalize(data.get("descripcion"))
    if not desc:
        return jsonify({"ok": False, "error": "La descripciÃ³n es obligatoria"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO fallas (descripcion) VALUES (%s)", (desc,))
        conn.commit()
        new_id = cur.lastrowid
    except IntegrityError:
        # clave Ãºnica duplicada
        return (
            jsonify({"ok": False, "error": "Ya existe una falla con esa descripciÃ³n"}),
            409,
        )
    finally:
        cur.close()
        conn.close()

    return jsonify({"ok": True, "id": new_id})


# =========================================================
#                CATÃLOGOS: REPARACIONES
# =========================================================

@app.route("/api/reparaciones", methods=["POST"])
def api_crear_reparacion():
    data = request.get_json()
    desc = to_capitalize(data.get("descripcion"))
    if not desc:
        return jsonify({"ok": False, "error": "La descripciÃ³n es obligatoria"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO reparaciones (descripcion) VALUES (%s)", (desc,))
        conn.commit()
        new_id = cur.lastrowid
    except IntegrityError:
        return (
            jsonify({"ok": False, "error": "Ya existe una reparaciÃ³n con esa descripciÃ³n"}),
            409,
        )
    finally:
        cur.close()
        conn.close()
    return jsonify({"ok": True, "id": new_id})



# =========================================================
#                     REPUESTOS
# =========================================================


@app.route("/api/repuestos", methods=["POST"])
def api_crear_repuesto():
    data = request.json or {}
    nombre = to_capitalize(data.get("nombre"))
    descripcion = to_capitalize(data.get("detalle") or data.get("descripcion"))
    costo = data.get("costo", 0)

    if not nombre:
        return jsonify({"ok": False, "error": "Falta nombre"}), 400

    try:
        costo = float(costo) if costo not in (None, "") else 0.0
    except:
        costo = 0.0

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO repuestos (nombre, descripcion, costo) VALUES (%s,%s,%s)",
        (nombre, descripcion, costo)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})



@app.route("/api/fallas/<int:falla_id>", methods=["DELETE"])
def api_borrar_falla(falla_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM fallas WHERE id=%s", (falla_id,))
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "Falla no encontrada"}), 404

        return jsonify({"ok": True})
    except Error as e:
        print("Error api_borrar_falla:", e)
        conn.rollback()
        return jsonify({"ok": False, "error": "Error al borrar falla"}), 500
    finally:
        cur.close()
        conn.close()


# =========================
# DELETE: REPARACIONES
# =========================
@app.route("/api/reparaciones/<int:reparacion_id>", methods=["DELETE"])
def api_borrar_reparacion(reparacion_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM reparaciones WHERE id=%s", (reparacion_id,))
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "ReparaciÃ³n no encontrada"}), 404

        return jsonify({"ok": True})
    except Error as e:
        print("Error api_borrar_reparacion:", e)
        conn.rollback()
        return jsonify({"ok": False, "error": "Error al borrar reparaciÃ³n"}), 500
    finally:
        cur.close()
        conn.close()


# =========================
# DELETE: REPUESTOS
# =========================
@app.route("/api/repuestos/<int:repuesto_id>", methods=["DELETE"])
def api_borrar_repuesto(repuesto_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM repuestos WHERE id=%s", (repuesto_id,))
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "Repuesto no encontrado"}), 404

        return jsonify({"ok": True})
    except Error as e:
        print("Error api_borrar_repuesto:", e)
        conn.rollback()
        return jsonify({"ok": False, "error": "Error al borrar repuesto"}), 500
    finally:
        cur.close()
        conn.close()
crear_equipo_api
@app.route("/api/ordenes/<int:orden_id>/docx", methods=["GET"])
def descargar_docx_orden(orden_id):
    filename = f"Orden_{orden_id}.docx"
    return send_from_directory(DOCX_DIR, filename, as_attachment=True)
@app.route("/api/ordenes/<int:orden_id>/reabrir", methods=["POST"])
def reabrir_orden(orden_id):
    motivo = (request.json or {}).get("motivo", "").strip()

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT estado FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    if o["estado"] not in ("TERMINADA", "RETIRADA"):
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Estado no permite reapertura"}), 400

    cur2 = conn.cursor()
    cur2.execute(
        "UPDATE ordenes SET estado=%s WHERE id=%s",
        ("EN REPARACION", orden_id)
    )
    conn.commit()

    _insert_hist(conn, orden_id, "REOPEN", motivo or "Reapertura")
    conn.commit()

    cur2.close(); cur.close(); conn.close()
    return jsonify({"ok": True})
@app.route("/api/ordenes/<int:orden_id>/suspender", methods=["POST"])
def suspender_orden(orden_id):
    motivo = (request.json or {}).get("motivo", "").strip()
    if not motivo:
        return jsonify({"ok": False, "error": "Motivo requerido"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT estado FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    if o["estado"] == "RETIRADA":
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "No se puede suspender una orden retirada"}), 400

    cur2 = conn.cursor()
    cur2.execute(
        "UPDATE ordenes SET estado=%s WHERE id=%s",
        ("SUSPENDIDA", orden_id)
    )
    conn.commit()

    _insert_hist(conn, orden_id, "SUSPEND", motivo)
    conn.commit()

    cur2.close(); cur.close(); conn.close()
    return jsonify({"ok": True})


@app.route("/api/ordenes/<int:orden_id>/duplicar", methods=["POST"])
def duplicar_orden(orden_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    copia = dict(o)
    copia.pop("id", None)

    copia["estado"] = "EN REPARACION"
    copia["fecha_salida"] = None
    copia["hora_salida"] = None
    copia["fecha_regreso"] = None
    copia["hora_regreso"] = None

    cols = list(copia.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    colnames = ", ".join(cols)

    cur2 = conn.cursor()
    cur2.execute(
        f"INSERT INTO ordenes ({colnames}) VALUES ({placeholders})",
        [copia[c] for c in cols]
    )
    new_id = cur2.lastrowid
    conn.commit()

    _insert_hist(conn, new_id, "DUPLICATE", f"Duplicada desde orden #{orden_id}")
    conn.commit()

    cur2.close(); cur.close(); conn.close()
    return jsonify({"ok": True, "id": new_id})

# ========= API Ã“RDENES =========
# =========================
# ORDENES: helpers
# =========================
import re
from flask import request, jsonify

ESTADOS_EN_PROCESO = {
    "EN REPARACION", "EN SOS", "EN WERTECH", "EN EKON",
    "EN AIR", "EN SERVIPRINT", "EN NICO GORI"
}
ESTADO_TERMINADA = "TERMINADA"
ESTADO_RETIRADA  = "RETIRADA"

def to_upper(s):
    return str(s or "").strip().upper()

def to_capitalize(s):
    """
    Normaliza texto:
    - strip
    - colapsa espacios
    - capitalize por oraciÃ³n simple (primera letra mayus, resto igual)
    Si querÃ©s TODO uppercase para textos tambiÃ©n, te lo cambio.
    """
    if s is None:
        return None
    t = str(s).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return None
    return t[:1].upper() + t[1:]

def parse_fecha(v):
    # espera YYYY-MM-DD
    if not v:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v[:10]

def parse_hora(v):
    # espera HH:MM
    if not v:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v[:5]

def now_fecha_hora():
    # usÃ¡ tu funciÃ³n existente si ya la tenÃ©s
    from datetime import datetime
    d = datetime.now()
    return d.strftime("%Y-%m-%d"), d.strftime("%H:%M")


# =========================
# POST /api/ordenes
# =========================
# =========================
# POST /api/ordenes
# =========================
@app.route("/api/ordenes", methods=["POST"])
def crear_orden():
    data = request.get_json(silent=True) or {}

    cliente_id = data.get("cliente_id")
    equipo_id  = data.get("equipo_id")
    if not cliente_id or not equipo_id:
        return jsonify({"ok": False, "error": "Cliente y equipo obligatorios"}), 400

    fecha_ingreso = parse_fecha(data.get("fecha")) or now_fecha_hora()[0]
    hora_ingreso  = parse_hora(data.get("hora_ingreso")) or now_fecha_hora()[1]
    estado = to_upper(data.get("estado") or "EN REPARACION")

    # âœ… presupuesto aprobado (0/1)
    try:
        presupuesto_aprobado = 1 if int(data.get("presupuesto_aprobado") or 0) == 1 else 0
    except:
        presupuesto_aprobado = 0

    falla         = to_capitalize(data.get("falla"))
    observaciones = to_capitalize(data.get("observaciones"))
    accesorios    = to_capitalize(data.get("accesorios"))
    reparacion    = to_capitalize(data.get("reparacion"))
    repuestos     = to_capitalize(data.get("repuestos"))

    try:
        importe = float(str(data.get("importe") or 0).replace(",", "."))
    except:
        importe = 0.0

    try:
        conn = get_db()
        cur = conn.cursor()
        branch = get_branch_config()
        registrado_por = session.get("username") or _usuario_actual()
        registrado_por_nombre = session.get("display_name") or registrado_por

        cur.execute("""
            INSERT INTO ordenes (
                fecha, hora_ingreso,
                cliente_id, equipo_id,
                falla, observaciones, accesorios,
                reparacion, repuestos,
                importe,
                estado,
                fecha_salida, hora_salida,
                fecha_regreso, hora_regreso,
                fecha_retiro, hora_retiro,
                presupuesto_aprobado,
                sucursal_key,
                registrado_por,
                registrado_por_nombre
            )
            VALUES (%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,
                    %s,
                    NULL,NULL,
                    NULL,NULL,
                    NULL,NULL,
                    %s,
                    %s,%s,%s)
        """, (
            fecha_ingreso, hora_ingreso,
            cliente_id, equipo_id,
            falla, observaciones, accesorios,
            reparacion, repuestos,
            importe,
            estado,
            presupuesto_aprobado,
            branch["key"],
            registrado_por,
            registrado_por_nombre,
        ))

        conn.commit()
        orden_id = cur.lastrowid

        # âœ… generar y ABRIR word al crear
        try:
            generar_word_de_orden(conn, orden_id, abrir=ABRIR_WORD_AL_CREAR)
        except Exception as e:
            print("WARN word:", e)

        cur.close()
        conn.close()
        return jsonify({"ok": True, "id": orden_id})

    except Exception as e:
        print("Error crear_orden:", e)
        return jsonify({"ok": False, "error": "Error al crear orden"}), 500


# =========================
# PUT /api/ordenes/<id>
# =========================
# =========================
# PUT /api/ordenes/<id>
# =========================
@app.route("/api/ordenes/<int:orden_id>", methods=["PUT"])
def actualizar_orden(orden_id):
    data = request.get_json(silent=True) or {}

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, cliente_id, equipo_id, estado,
                   fecha_salida, hora_salida,
                   fecha_regreso, hora_regreso,
                   fecha_retiro, hora_retiro,
                   presupuesto_aprobado
            FROM ordenes
            WHERE id=%s
        """, (orden_id,))
        actual = cur.fetchone()

        if not actual:
            cur.close(); conn.close()
            return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

        cliente_id = data.get("cliente_id") or actual["cliente_id"]
        equipo_id  = data.get("equipo_id")  or actual["equipo_id"]

        # bloquear cambio de equipo SOLO si el front lo manda distinto
        if data.get("equipo_id") and str(data.get("equipo_id")) != str(actual["equipo_id"]):
            cur.close(); conn.close()
            return jsonify({"ok": False, "error": "No se puede cambiar el equipo de la orden"}), 409

        estado_actual = to_upper(actual.get("estado") or "EN REPARACION")
        estado_nuevo  = to_upper(data.get("estado") or estado_actual)

        # âœ… presupuesto aprobado: si no viene, conservar DB
        pa_raw = data.get("presupuesto_aprobado", actual.get("presupuesto_aprobado", 0))
        try:
            presupuesto_aprobado = 1 if int(pa_raw) == 1 else 0
        except:
            presupuesto_aprobado = 0

        falla         = to_capitalize(data.get("falla"))
        observaciones = to_capitalize(data.get("observaciones"))
        accesorios    = to_capitalize(data.get("accesorios"))
        reparacion    = to_capitalize(data.get("reparacion"))
        repuestos     = to_capitalize(data.get("repuestos"))

        try:
            importe = float(str(data.get("importe") or 0).replace(",", "."))
        except:
            importe = 0.0

        fecha_salida  = parse_fecha(data.get("fecha_salida"))  or actual["fecha_salida"]
        hora_salida   = parse_hora(data.get("hora_salida"))    or actual["hora_salida"]
        fecha_regreso = parse_fecha(data.get("fecha_regreso")) or actual["fecha_regreso"]
        hora_regreso  = parse_hora(data.get("hora_regreso"))   or actual["hora_regreso"]
        fecha_retiro  = parse_fecha(data.get("fecha_retiro"))  or actual["fecha_retiro"]
        hora_retiro   = parse_hora(data.get("hora_retiro"))    or actual["hora_retiro"]

        # ---------- reglas de transiciones ----------
        if estado_actual in ESTADOS_EN_PROCESO and estado_nuevo == ESTADO_TERMINADA:
            if not fecha_salida:
                fecha_salida, hora_salida = now_fecha_hora()

        if estado_actual == ESTADO_TERMINADA and estado_nuevo in ESTADOS_EN_PROCESO:
            if not fecha_regreso:
                fecha_regreso, hora_regreso = now_fecha_hora()

        if estado_nuevo == ESTADO_RETIRADA:
            if estado_actual != ESTADO_TERMINADA:
                cur.close(); conn.close()
                return jsonify({"ok": False, "error": "Para retirar, la orden debe estar TERMINADA"}), 400
            if not fecha_retiro:
                fecha_retiro, hora_retiro = now_fecha_hora()

        cur2 = conn.cursor()
        cur2.execute("""
            UPDATE ordenes
            SET cliente_id=%s,
                equipo_id=%s,
                falla=%s,
                observaciones=%s,
                accesorios=%s,
                reparacion=%s,
                repuestos=%s,
                importe=%s,
                estado=%s,
                fecha_salida=%s,
                hora_salida=%s,
                fecha_regreso=%s,
                hora_regreso=%s,
                fecha_retiro=%s,
                hora_retiro=%s,
                presupuesto_aprobado=%s
            WHERE id=%s
        """, (
            cliente_id,
            equipo_id,
            falla,
            observaciones,
            accesorios,
            reparacion,
            repuestos,
            importe,
            estado_nuevo,
            fecha_salida,
            hora_salida,
            fecha_regreso,
            hora_regreso,
            fecha_retiro,
            hora_retiro,
            presupuesto_aprobado,
            orden_id
        ))

        conn.commit()

        # âœ… regenerar Word cada vez que se modifica (y opcional abrir)
        try:
            generar_word_de_orden(conn, orden_id, abrir=ABRIR_WORD_AL_MODIFICAR)
        except Exception as e:
            print("WARN word:", e)

        cur2.close()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    except Exception as e:
        print("Error actualizar_orden:", e)
        return jsonify({"ok": False, "error": "Error al actualizar orden"}), 500

@app.route("/api/ordenes/<int:orden_id>", methods=["GET"])
def api_orden_por_id(orden_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            o.*,
            c.nombre   AS nombre_contacto,
            COALESCE(NULLIF(TRIM(c.telefono),''), NULLIF(TRIM(c.celular),''), '') AS telefono_contacto,
            e.serie    AS serie_texto,
            CONCAT_WS(' ', e.descripcion, e.marca, e.modelo) AS equipo_texto
        FROM ordenes o
        LEFT JOIN """ + shared_table("clientes") + """ c ON c.id = o.cliente_id
        LEFT JOIN """ + shared_table("equipos") + """ e ON e.id = o.equipo_id
        WHERE o.id=%s
        LIMIT 1
    """, (orden_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    row = normalize_row(row)
    row["sucursal_nombre"] = branch_name(row.get("sucursal_key"))
    return jsonify(row)



    return jsonify(row)
@app.route("/api/ordenes/<int:orden_id>/retirar", methods=["POST"])
def orden_retirar(orden_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, estado, fecha_retiro, hora_retiro FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    if o["estado"] != "TERMINADA":
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Para retirar, la orden debe estar TERMINADA"}), 400

    if not o["fecha_retiro"]:
        f, h = now_fecha_hora()
    else:
        f, h = o["fecha_retiro"], o["hora_retiro"]

    cur2 = conn.cursor()
    cur2.execute("""
        UPDATE ordenes
        SET estado='RETIRADA', fecha_retiro=%s, hora_retiro=%s
        WHERE id=%s
    """, (f, h, orden_id))
    conn.commit()
    cur2.close()

    cur.close(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/ordenes/<int:orden_id>/terminar", methods=["POST"])
def orden_terminar(orden_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, estado, fecha_terminada, hora_terminada FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    if o["estado"] == "RETIRADA":
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "La orden ya estÃ¡ retirada"}), 400

    # si no estÃ¡ seteado, lo seteamos ahora
    if not o.get("fecha_terminada"):
        f, h = now_fecha_hora()
    else:
        f, h = o["fecha_terminada"], o["hora_terminada"]

    cur2 = conn.cursor()
    cur2.execute("""
        UPDATE ordenes
        SET estado='TERMINADA',
            fecha_terminada=%s,
            hora_terminada=%s
        WHERE id=%s
    """, (f, h, orden_id))
    conn.commit()
    cur2.close()

    cur.close(); conn.close()
    return jsonify({"ok": True})


@app.route("/api/ordenes/<int:orden_id>/salida", methods=["POST"])
def orden_registrar_salida(orden_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, estado, fecha_salida, hora_salida FROM ordenes WHERE id=%s", (orden_id,))
    o = cur.fetchone()
    if not o:
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "Orden no encontrada"}), 404

    if o["estado"] == "RETIRADA":
        cur.close(); conn.close()
        return jsonify({"ok": False, "error": "La orden ya estÃ¡ retirada"}), 400

    if not o["fecha_salida"]:
        f, h = now_fecha_hora()
        cur2 = conn.cursor()
        cur2.execute("""
            UPDATE ordenes SET fecha_salida=%s, hora_salida=%s
            WHERE id=%s
        """, (f, h, orden_id))
        conn.commit()
        cur2.close()

    cur.close(); conn.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    # host 0.0.0.0 para que lo vean otras PCs de la red
    app.run(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=env_bool("FLASK_DEBUG", False),
    )
