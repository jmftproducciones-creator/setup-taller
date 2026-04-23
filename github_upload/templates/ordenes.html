{% extends "base.html" %}

{% block title %}Setup - Órdenes{% endblock %}

{% block content %}
<script>
  window.__APP_CONTEXT__ = {{ (app_context or {})|tojson }};
</script>

<div id="authOverlay" class="auth-overlay{% if app_context and app_context.authenticated %} is-hidden{% endif %}">
  <div class="auth-card">
    <div class="auth-eyebrow">Acceso por sucursal</div>
    <h2>Ingreso al sistema</h2>
    <p class="auth-copy">Cada usuario entra con su contraseña hasheada y trabaja sobre la base de datos de la sucursal elegida.</p>
    <form id="loginForm" class="auth-form">
      <label>
        <span>Usuario</span>
        <input id="loginUsername" name="username" type="text" autocomplete="username" required>
      </label>
      <label>
        <span>Contraseña</span>
        <input id="loginPassword" name="password" type="password" autocomplete="current-password" required>
      </label>
      <label>
        <span>Sucursal</span>
        <select id="loginBranch" name="branch_key" required>
          <option value="">-- Seleccionar sucursal --</option>
          {% for branch in (app_context.available_branches if app_context else []) %}
          <option value="{{ branch.key }}">{{ branch.name }}</option>
          {% endfor %}
        </select>
      </label>
      <button id="btnLogin" type="submit">Ingresar</button>
    </form>
  </div>
</div>

<div class="layout-setup">
  <div class="session-bar">
    <div>
      <strong id="sessionUserName">{{ app_context.display_name if app_context and app_context.display_name else 'Sin sesión' }}</strong>
      <span id="sessionBranchName">{{ app_context.branch.name if app_context and app_context.branch else 'Sucursal no seleccionada' }}</span>
    </div>
    <div class="session-actions">
      <select id="branchSwitcher"{% if not (app_context and app_context.authenticated) %} disabled{% endif %}>
        <option value="">-- Cambiar sucursal --</option>
        {% for branch in (app_context.allowed_branches if app_context else []) %}
        <option value="{{ branch.key }}"{% if app_context and app_context.branch and app_context.branch.key == branch.key %} selected{% endif %}>{{ branch.name }}</option>
        {% endfor %}
      </select>
      <button id="btnProfile" type="button"{% if not (app_context and app_context.authenticated) %} disabled{% endif %}>Mi perfil</button>
      <button id="btnLogout" type="button"{% if not (app_context and app_context.authenticated) %} disabled{% endif %}>Cerrar sesión</button>
    </div>
  </div>

  <div id="profileModal" class="profile-modal is-hidden">
    <div class="profile-card">
      <div class="profile-header">
        <div>
          <strong>Mi perfil</strong>
          <span>Podés actualizar tus datos y contraseña.</span>
        </div>
        <button id="btnProfileClose" type="button">Cerrar</button>
      </div>
      <form id="profileForm" class="profile-form">
        <label>
          <span>Usuario</span>
          <input id="profileUsername" type="text" required>
        </label>
        <label>
          <span>Nombre a mostrar</span>
          <input id="profileDisplayName" type="text" required>
        </label>
        <label>
          <span>Email</span>
          <input id="profileEmail" type="email">
        </label>
        <label>
          <span>Teléfono</span>
          <input id="profileTelefono" type="text">
        </label>
        <label>
          <span>Nueva contraseña</span>
          <input id="profilePassword" type="password" placeholder="Dejar vacío para no cambiar">
        </label>
        <button id="btnProfileSave" type="submit">Guardar perfil</button>
      </form>
    </div>
  </div>

  {% if app_context and app_context.is_admin %}
  <div id="userModal" class="profile-modal is-hidden">
    <div class="profile-card user-card">
      <div class="profile-header">
        <div>
          <strong id="userModalTitle">Nuevo usuario</strong>
          <span>Creá o editá usuarios, sucursales y permisos.</span>
        </div>
        <button id="btnUserModalClose" type="button">Cerrar</button>
      </div>
      <form id="userForm" class="profile-form">
        <input id="usuario_id" type="hidden">
        <label>
          <span>Usuario</span>
          <input id="usuario_username" type="text" required>
        </label>
        <label>
          <span>Nombre</span>
          <input id="usuario_display_name" type="text" required>
        </label>
        <label>
          <span>Email</span>
          <input id="usuario_email" type="email">
        </label>
        <label>
          <span>Teléfono</span>
          <input id="usuario_telefono" type="text">
        </label>
        <label>
          <span>Contraseña</span>
          <input id="usuario_password" type="password" placeholder="Obligatoria al crear">
        </label>
        <div class="modal-grid-2">
          <label class="profile-check">
            <input id="usuario_branch_central" type="checkbox" value="central">
            <span>Sucursal Verde</span>
          </label>
          <label class="profile-check">
            <input id="usuario_branch_naranja" type="checkbox" value="naranja">
            <span>Sucursal Naranja</span>
          </label>
        </div>
        <div class="modal-grid-2">
          <label class="profile-check">
            <input id="usuario_is_admin" type="checkbox">
            <span>Administrador</span>
          </label>
          <label class="profile-check">
            <input id="usuario_activo" type="checkbox" checked>
            <span>Activo</span>
          </label>
        </div>
        <button id="btnUsuarioGuardar" type="submit">Guardar usuario</button>
      </form>
    </div>
  </div>
  {% endif %}

  <!-- ================== TABS ================== -->
  <div class="tabs">
    <button class="tab-button active" data-tab="form">Formulario</button>
    <button class="tab-button" data-tab="lista">Lista de órdenes</button>
    <button class="tab-button" data-tab="clientes">Clientes</button>
    <button class="tab-button" data-tab="equipos">Equipos</button>
    <button class="tab-button" data-tab="catalogos">Catálogos</button>
    {% if app_context and app_context.is_admin %}
    <button class="tab-button" data-tab="usuarios">Usuarios</button>
    {% endif %}
  </div>
  <div class="logo-box logo-nbf-fixed">
      <img src="{{ url_for('static', filename='NBFSOFT.png') }}" alt="NBFSOFT.png">
    </div>
  <div class="tab-content">

    <!-- ============ TAB FORMULARIO ORDEN ============ -->
    <div id="form" class="tab-pane active">
  <div class="panel panel-form">

    <div class="header-form">
      <div class="buscar-box">
        <label for="buscar_nro">N°</label>
        <input type="number" id="buscar_nro" min="1" style="width: 100px;">
        <button id="btnBuscar" type="button">BUSCAR</button>
        <button id="btnLimpiar" style="background:#555;" type="button">LIMPIAR</button>
      </div>

      <div class="titulo-form">CONSULTA Y MODIFICA</div>

      <div class="estado-actual">
        <span>ESTADO:</span>
        <span id="estado_display" class="estado-display">EN REPARACION</span>
      </div>

      <div class="logo-box">
        <img src="{{ url_for('static', filename='logo.png') }}" alt="SETUP">
      </div>
    </div>

    <div class="form-grid">

      <!-- ======================
           PARTE 1: ALTA (NUEVA ORDEN)
           Solo hasta Accesorios
           ====================== -->
      <div id="form_parte_alta" class="span-2" style="grid-column: 1 / -1;">
        <div class="form-grid" style="padding:0;">

          <div class="campo-row">
            <label for="nro">N° interno:</label>
            <input type="text" id="nro" readonly>
          </div>

          <div class="campo-row">
            <label for="fecha">Fecha ingreso:</label>
            <input type="date" id="fecha" readonly>
          </div>

          <div class="campo-row">
            <label for="cliente_select_form">Cliente / contacto:</label>
            <div style="display:flex; gap:6px; width:100%; flex-direction:column;">
              <input id="cliente_form_search" type="text" placeholder="Buscar cliente por nombre/teléfono/email..." style="max-width:320px;">
              <select id="cliente_select_form">
                <option value="">-- Seleccionar cliente --</option>
              </select>
            </div>
          </div>

          <div class="campo-row">
            <label for="telefono">Teléfono:</label>
            <input type="text" id="telefono">
          </div>

          <div class="campo-row">
            <label for="equipo_select_form">Equipo:</label>
            <div style="display:flex; gap:6px; width:100%; flex-direction:column;">
              <input id="equipo_form_search" type="text" placeholder="Buscar equipo por descripción/serie/marca..." style="max-width:320px;">
              <select id="equipo_select_form">
                <option value="">-- Seleccionar equipo --</option>
              </select>
            </div>
          </div>

          <div class="campo-row">
            <label for="serie">S/N:</label>
            <input type="text" id="serie" readonly>
          </div>

          <!-- FALLA -->
          

          <div class="campo-row">
            <label for="observaciones">Observaciones:</label>
            <input type="text" id="observaciones">
          </div>

          <div class="campo-row">
            <label for="accesorios">Accesorios:</label>
            <input type="text" id="accesorios">
          </div>

        </div>
      </div>
      <div class="campo-row span-2">
            <label for="falla_select">Falla:</label>
            <div style="display:flex; gap:6px; width:100%;">
              <div style="flex:0 0 280px; display:flex; flex-direction:column; gap:6px;">
                <input id="falla_search" type="text" placeholder="Buscar falla (texto, palabras, etc.)">
                <select id="falla_select" multiple size="4" style="width:100%;">
                  <option value="">-- Seleccionar falla --</option>
                </select>
              </div>
              <button id="btnFallaPlus" type="button">+</button>
              <input type="text" id="falla_comentario" placeholder="Comentario adicional" style="flex:1;">
            </div>
          </div>
      <!-- ======================
           PARTE 2: MODIFICACIÓN
           Aparece solo cuando hay nro (orden cargada)
           ====================== -->
      <div id="form_parte_mod" class="span-2 is-hidden" style="grid-column: 1 / -1;">
        <div class="form-grid" style="padding:0;">

          <!-- REPARACIÓN -->
          <div class="campo-row span-2">
            <label for="reparacion_select">Reparación:</label>
            <div style="display:flex; gap:6px; width:100%;">
              <div style="flex:0 0 280px; display:flex; flex-direction:column; gap:6px;">
                <input id="reparacion_search" type="text" placeholder="Buscar reparación...">
                <select id="reparacion_select" multiple size="4" style="width:100%;">
                  <option value="">-- Seleccionar reparación --</option>
                </select>
              </div>
              <button id="btnReparacionPlus" type="button">+</button>
              <input type="text" id="reparacion_comentario" placeholder="Comentario adicional" style="flex:1;">
            </div>
          </div>

          <!-- REPUESTOS -->
          <div class="campo-row span-2">
            <label for="repuesto_select">Repuestos:</label>
            <div style="display:flex; gap:6px; width:100%;">
              <div style="flex:0 0 280px; display:flex; flex-direction:column; gap:6px;">
                <input id="repuesto_search" type="text" placeholder="Buscar repuesto (nombre/detalle/costo)...">
                <select id="repuesto_select" multiple size="4" style="width:100%;">
                  <option value="">-- Seleccionar repuesto --</option>
                </select>
              </div>
              <button id="btnRepuestoPlus" type="button">+</button>
              <input type="text" id="repuesto_comentario" placeholder="Comentario adicional" style="flex:1;">
            </div>
          </div>

          <div class="campo-row">
            <label for="importe">Importe:</label>
            <div style="display:flex; gap:8px; width:100%; align-items:center;">
              <input type="number" id="importe" step="0.01" readonly>
              <button type="button" id="btnToggleImporte">Editar importe</button>
            </div>
          </div>
          <div class="campo-row">
            <label style="display:flex; align-items:center; gap:10px;">
              <input type="checkbox" id="presupuesto_aprobado">
              Presupuesto aprobado
            </label>
          </div>

          <div class="campo-row">
            <label for="estado">Cambiar estado:</label>
            <select id="estado">
              <option value="EN REPARACION">EN REPARACION</option>
              <option value="EN SOS">EN SOS</option>
              <option value="EN WERTECH">EN WERTECH</option>
              <option value="EN EKON">EN EKON</option>
              <option value="SUSPENDIDA">SUSPENDIDA</option>
              <option value="EN AIR">EN AIR</option>
              <option value="EN SERVIPRINT">EN SERVIPRINT</option>
              <option value="EN NICO GORI">EN NICO GORI</option>
              <option value="TERMINADA">TERMINADA</option>
              <option value="RETIRADA">RETIRADA</option>
            </select>
          </div>

          <div class="campo-row">
            <label for="fecha_salida">Fecha salida:</label>
            <input type="date" id="fecha_salida" readonly>
          </div>

          <div class="campo-row">
            <label for="fecha_regreso">Fecha regreso:</label>
            <input type="date" id="fecha_regreso" readonly>
          </div>

          <div id="retiro_box" class="campo-row span-2 is-hidden" style="grid-column: 1 / -1;">
            <strong>Retirada:</strong>
            <span id="retiro_texto">—</span>
          </div>

        </div>
      </div>

    </div>

    <!-- Hidden fields (quedan igual) -->
    <input type="hidden" id="hora_ingreso">
    <input type="hidden" id="hora_salida">
    <input type="hidden" id="hora_regreso">

    <!-- Botonera -->
    <div class="botonera-form">
      <button id="btnAgregar" type="button">AGREGAR</button>

      <button id="btnModificar" type="button" class="is-hidden">MODIFICAR</button>
      <button type="button" id="btnRegistrarSalida" class="is-hidden">Registrar salida</button>
      <button type="button" id="btnMarcarTerminada" class="is-hidden">Marcar terminada</button>
      <button type="button" id="btnMarcarRetirada" class="is-hidden">Marcar retirada</button>
    </div>

  </div>
</div>


    <!-- ============ TAB LISTA ORDENES ============ -->
    <div id="lista" class="tab-pane">
      <div class="panel panel-lista">
        <div class="lista-header">
          <h3>Órdenes cargadas</h3>
          <div class="lista-busqueda">
            <input type="text" id="filtro_texto" placeholder="Filtrar por nombre/equipo...">
            <button id="btnRefrescarLista" type="button">Refrescar</button>
            
          </div>
        </div>
        <div class="acciones-lista" style="display:flex; gap:8px; margin: 10px 0;">
          <button id="btnDuplicarDesdeLista" type="button" disabled>Duplicar</button>
          <button id="btnReabrirDesdeLista" type="button" disabled>Reabrir</button>
          <label for="estado_filtro">Estado:</label>
            <select id="estado_filtro">
              <option value="">-- Todos --</option>
            </select>

        </div>


        <div class="lista-contenedor">
          <table id="tablaOrdenes">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>N°</th>
                <th>Cliente</th>
                <th>Equipo</th>
                <th>Observación</th>
                <th>Registró</th>
                <th>Sucursal</th>
                <th>Estado</th>
                <th>PA</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
        <p class="lista-tip">Tip: hacé click en una orden para cargarla en el formulario.</p>
      </div>
    </div>

    <!-- ============ TAB CLIENTES ============ -->
    <div id="clientes" class="tab-pane">
      <div class="panel panel-clientes">
        <h3>Clientes</h3>

        

        <div class="form-grid">
          <div class="campo-row">
            <label for="cliente_id">ID:</label>
            <input id="cliente_id" type="text" readonly>
          </div>
          <div class="campo-row">
            <label for="cliente_nombre">Nombres:</label>
            <input id="cliente_nombre" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_direccion">Dirección:</label>
            <input id="cliente_direccion" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_localidad">Localidad:</label>
            <input id="cliente_localidad" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_provincia">Estado/Provincia:</label>
            <input id="cliente_provincia" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_cp">CP:</label>
            <input id="cliente_cp" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_telefono">Teléfono:</label>
            <input id="cliente_telefono" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_celular">Celular:</label>
            <input id="cliente_celular" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_email">E-mail:</label>
            <input id="cliente_email" type="email">
          </div>
          <div class="campo-row">
            <label for="cliente_cuit">CUIT:</label>
            <input id="cliente_cuit" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_contacto">Contacto:</label>
            <input id="cliente_contacto" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_observaciones">Observaciones:</label>
            <input id="cliente_observaciones" type="text">
          </div>
          <div class="campo-row">
            <label for="cliente_giro">Giro de la empresa:</label>
            <input id="cliente_giro" type="text">
          </div>
          <div class="campo-row">
            <label>Opciones:</label>
            <div>
              <label><input type="checkbox" id="cliente_garantia"> Cliente Garantía</label>
              <label style="margin-left:20px;"><input type="checkbox" id="cliente_contrato"> Cliente con Contrato</label>
            </div>
          </div>
        </div>
        <div class="campo-row">
          <label for="cliente_filtro">Filtrar por nombre...</label>
          <input id="cliente_filtro" type="text">
          <button id="btnClienteNuevo" type="button">nuevo</button>
          <button id="btn_limpiar_cliente" type="button">Limpiar</button>

          <button id="btnClienteGuardar" type="button">Guardar</button>
        </div>
        <table id="tablaClientes">
          <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Teléfono</th>
            <th>Dirección</th>
            <th>Localidad</th>
          </tr>
          </thead>
          <tbody></tbody>
        </table>
        <p class="lista-tip">Click en un cliente para editarlo y usarlo en las órdenes.</p>
      </div>
    </div>

    <!-- ============ TAB EQUIPOS ============ -->
    <div id="equipos" class="tab-pane">
      <div class="panel panel-equipos">
        <h3>Equipos</h3>

        

        <div class="form-grid">
          <div class="campo-row">
            <label for="equipo_id">ID:</label>
            <input id="equipo_id" type="text" readonly>
          </div>
          <div class="campo-row">
            <label for="equipo_descripcion">Descripción:</label>
            <input id="equipo_descripcion" type="text">
          </div>
          <div class="campo-row">
            <label for="equipo_serie">Serie:</label>
            <input id="equipo_serie" type="text">
          </div>
          <div class="campo-row">
            <label for="equipo_tipo">Tipo de equipo:</label>
            <input id="equipo_tipo" type="text">
          </div>
          <div class="campo-row">
            <label for="equipo_marca">Marca:</label>
            <input id="equipo_marca" type="text">
          </div>
          <div class="campo-row">
            <label for="equipo_modelo">Modelo:</label>
            <input id="equipo_modelo" type="text">
          </div>
          <div class="campo-row">
            <label for="equipo_cliente_select">Cliente:</label>
            <select id="equipo_cliente_select">
              <option value="">-- Seleccionar cliente --</option>
            </select>
          </div>
        </div>

        <p class="lista-tip">Cada equipo debe estar vinculado al menos a un cliente.</p>
        <div class="campo-row">
          <label for="equipo_filtro">Filtrar por descripción/serie</label>
          <input id="equipo_filtro" type="text">
          <button id="btnEquipoNuevo" type="button">nuevo</button>
          <button id="btn_limpiar_equipo" type="button">Limpiar</button>

          <button id="btnEquipoGuardar" type="button">Guardar</button>
        </div>
        <table id="tablaEquipos">
          <thead>
            <tr>
              <th>ID</th>
              <th>Descripción</th>
              <th>Serie</th>
              <th>Tipo</th>
              <th>Marca</th>
              <th>Modelo</th>
              <th>Clientes</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
        <p class="lista-tip">Click en un equipo para editarlo.</p>
      </div>
    </div>

    <!-- ============ TAB CATALOGOS (Fallas, Reparaciones, Repuestos) ============ -->
    <div id="catalogos" class="tab-pane">
  <div class="panel panel-catalogos">
    <h3>Catálogos</h3>

    <!-- Sub-tabs internos -->
    <div class="tabs" style="margin: 10px 14px 0; border-radius: 12px;">
      <button class="tab-button active" type="button" data-cat="cat_fr">Fallas + Reparaciones</button>
      <button class="tab-button" type="button" data-cat="cat_rep">Repuestos</button>
    </div>

    <div style="padding: 12px 14px 14px;">

      <!-- ======================
           CAT 1: Fallas + Reparaciones
           ====================== -->
      <div id="cat_fr" class="cat-pane active">
        <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:16px;">

          <!-- FALLAS -->
          <div>
            <h4>Fallas</h4>
            <div class="campo-row">
              <label for="cat_falla_desc">Descripción:</label>
              <input id="cat_falla_desc" type="text">
            </div>
            <button id="btnCatFallaGuardar" type="button">Guardar falla</button>

            <div class="campo-row" style="margin-top:6px;">
              <label for="cat_falla_filtro">Buscar:</label>
              <input id="cat_falla_filtro" type="text" placeholder="Buscar por id o descripción...">
            </div>

            <table id="tablaCatFallas" style="margin-top:8px; font-size:12px;">
              <thead><tr><th>ID</th><th>Descripción</th><th>Acciones</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>

          <!-- REPARACIONES -->
          <div>
            <h4>Reparaciones</h4>
            <div class="campo-row">
              <label for="cat_rep_desc">Descripción:</label>
              <input id="cat_rep_desc" type="text">
            </div>
            <button id="btnCatReparacionGuardar" type="button">Guardar reparación</button>

            <div class="campo-row" style="margin-top:6px;">
              <label for="cat_rep_filtro">Buscar:</label>
              <input id="cat_rep_filtro" type="text" placeholder="Buscar por id o descripción...">
            </div>

            <table id="tablaCatReparaciones" style="margin-top:8px; font-size:12px;">
              <thead><tr><th>ID</th><th>Descripción</th><th>Acciones</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>

        </div>
      </div>

      <!-- ======================
           CAT 2: Repuestos
           ====================== -->
      <div id="cat_rep" class="cat-pane" style="display:none;">
        <div style="max-width: 760px;">

          <h4>Repuestos</h4>

          <div class="campo-row">
            <label for="cat_rep_nombre">Nombre:</label>
            <input id="cat_rep_nombre" type="text">
          </div>

          <div class="campo-row">
            <label for="cat_rep_detalle">Detalle:</label>
            <input id="cat_rep_detalle" type="text">
          </div>

          <div class="campo-row">
            <label for="cat_rep_costo">Costo:</label>
            <input id="cat_rep_costo" type="number" step="0.01">
          </div>

          <button id="btnCatRepuestoGuardar" type="button">Guardar repuesto</button>

          <div class="campo-row" style="margin-top:6px;">
            <label for="cat_repuesto_filtro">Buscar:</label>
            <input id="cat_repuesto_filtro" type="text" placeholder="Buscar por nombre/detalle/costo/id...">
          </div>

          <table id="tablaCatRepuestos" style="margin-top:8px; font-size:12px;">
            <thead>
              <tr><th>ID</th><th>Nombre</th><th>Descripción</th><th>Costo</th><th>Acciones</th></tr>
            </thead>
            <tbody></tbody>
          </table>

        </div>
      </div>

    </div>

    <p class="lista-tip">Estas listas se usan en el formulario principal para las opciones de Falla, Reparación y Repuestos.</p>
  </div>
</div>

    {% if app_context and app_context.is_admin %}
    <div id="usuarios" class="tab-pane">
      <div class="panel panel-usuarios">
        <h3>Usuarios</h3>
        <div class="campo-row">
          <label for="usuario_filtro">Filtrar usuario</label>
          <input id="usuario_filtro" type="text" placeholder="Buscar por usuario, nombre o sucursal">
          <button id="btnUsuarioNuevo" type="button">Nuevo</button>
          <button id="btnUsuarioEditar" type="button" disabled>Editar</button>
        </div>
        <table id="tablaUsuarios">
          <thead>
            <tr>
              <th>ID</th>
              <th>Usuario</th>
              <th>Nombre</th>
              <th>Sucursales</th>
              <th>Admin</th>
              <th>Activo</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
        <p class="lista-tip">Click en un usuario para editarlo. Si dejás la contraseña vacía al editar, se conserva la actual.</p>
      </div>
    </div>
    {% endif %}


  </div> <!-- /tab-content -->
</div>  <!-- /layout-setup -->
<div id="toast" class="toast" style="display:none;"></div>
<!-- Loading overlay -->
<div id="loadingOverlay" class="loading-overlay" aria-hidden="true">
  <div class="loading-card">
    <img class="loading-logo" src="{{ url_for('static', filename='NBFSOFT.png') }}" alt="NBF Soft">
    <div class="loading-text">Cargando…</div>
    <div class="loading-subtext">Sincronizando datos</div>
  </div>
</div>


<script src="{{ url_for('static', filename='setup.js') }}" defer></script>
{% endblock %}
