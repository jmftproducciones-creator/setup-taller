
import pandas as pd
import mysql.connector
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

def load_env_file(path: Path = PROJECT_DIR / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "setup_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

# Nombre del archivo Excel a importar (en la misma carpeta que el .py)
EXCEL_FILE = BASE_DIR / "articulos.xlsx"
SHEET_NAME = 0  # primera hoja


# -------------------------
# FUNCIONES AUXILIARES
# -------------------------
def s(val):
    """Convierte valores de pandas a str o None, quitando NaN y espacios."""
    if pd.isna(val):
        return None
    text = str(val).strip()
    return text or None


def s_float(val):
    """Convierte a float o None (para costos)."""
    if pd.isna(val) or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        try:
            return float(str(val).replace(",", "."))
        except Exception:
            return None


def s_int(val):
    """Convierte a int o None (sirve para CODIGO)."""
    if pd.isna(val) or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return int(float(val))
        except Exception:
            return None


# -------------------------
# IMPORTAR REPUESTOS
# -------------------------
def importar_repuestos_desde_excel(ruta_excel: str):
    print(f"Leyendo archivo Excel: {ruta_excel} ...")

    # El Excel NO tiene encabezados -> header=None
    df = pd.read_excel(ruta_excel, sheet_name=SHEET_NAME, header=None)

    # Asignar nombres de columna manualmente, en el orden exacto que nos diste
    df.columns = [
        "CODIGO",
        "DESCRIP",
        "UNIDAD",
        "COSTO",
        "COSTO1",
        "COSTO2",
        "EXIST",
        "EXIST_MIN",
        "COD_MAR",
        "ABRE_MAR",
        "FEC_COMPR",
        "IVA",
        "COD_BARRA",
        "COD_PROVE",
        "TILDE",
        "ORDEN",
        "CAN_SELECT",
        "OBSERVA",
        "IMP_INT",
        "POR_GAN",
        "FEC_MODIF",
        "COD_BAR",
    ]

    print("Columnas asignadas al DataFrame:")
    print(list(df.columns))

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    filas_ok = 0
    filas_err = 0

    for idx, row in df.iterrows():
        try:
            # ----- Mapear columnas del Excel a los campos de la tabla repuestos -----
            codigo = s_int(row["CODIGO"])        # id del repuesto
            nombre = s(row["DESCRIP"])           # descripciÃ³n corta / nombre
            if not nombre:
                raise ValueError("Repuesto sin DESCRIP, se omite.")

            # costo base: usamos COSTO (podÃ©s cambiar a COSTO1 o COSTO2 si querÃ©s)
            costo = s_float(row["COSTO"])

            # Armar descripciÃ³n larga con otros datos Ãºtiles
            desc_partes = []

            unidad = s(row["UNIDAD"])
            if unidad:
                desc_partes.append(f"Unidad: {unidad}")

            marca = s(row["ABRE_MAR"]) or s(row["COD_MAR"])
            if marca:
                desc_partes.append(f"Marca: {marca}")

            cod_barra = s(row["COD_BARRA"]) or s(row["COD_BAR"])
            if cod_barra:
                desc_partes.append(f"CÃ³digo de barras: {cod_barra}")

            cod_prove = s(row["COD_PROVE"])
            if cod_prove:
                desc_partes.append(f"CÃ³d. proveedor: {cod_prove}")

            exist = s(row["EXIST"])
            exist_min = s(row["EXIST_MIN"])
            if exist or exist_min:
                desc_partes.append(f"Stock: {exist or '-'} / MÃ­nimo: {exist_min or '-'}")

            iva = s(row["IVA"])
            if iva:
                desc_partes.append(f"IVA: {iva}")

            imp_int = s(row["IMP_INT"])
            if imp_int:
                desc_partes.append(f"Imp. interno: {imp_int}")

            por_gan = s(row["POR_GAN"])
            if por_gan:
                desc_partes.append(f"Ganancia: {por_gan}%")

            obs = s(row["OBSERVA"])
            if obs:
                desc_partes.append(f"Obs: {obs}")

            fec_compr = s(row["FEC_COMPR"])
            if fec_compr:
                desc_partes.append(f"Ãšltima compra: {fec_compr}")

            fec_modif = s(row["FEC_MODIF"])
            if fec_modif:
                desc_partes.append(f"Ãšltima modificaciÃ³n: {fec_modif}")

            descripcion = " | ".join(desc_partes) if desc_partes else None

            # Si no hay cÃ³digo, podemos dejar que MySQL autoasigne id (None)
            # pero si tu tabla repuestos usa PK AUTO_INCREMENT, estÃ¡ bien.
            # Igual, si CODIGO viene siempre, lo usamos para que coincida con el otro sistema.

            # ----- INSERT / UPDATE en la tabla repuestos -----
            cur.execute(
                """
                INSERT INTO repuestos (id, nombre, descripcion, costo)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nombre = VALUES(nombre),
                    descripcion = VALUES(descripcion),
                    costo = VALUES(costo)
                """,
                (
                    codigo,
                    nombre,
                    descripcion,
                    costo,
                ),
            )
            filas_ok += 1
        except Exception as e:
            filas_err += 1
            print(f"[Fila {idx + 1}] Error importando repuesto: {e}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"ImportaciÃ³n de repuestos finalizada. OK: {filas_ok}, con error: {filas_err}")


if __name__ == "__main__":
    importar_repuestos_desde_excel(str(EXCEL_FILE))
