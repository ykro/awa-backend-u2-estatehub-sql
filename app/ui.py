from __future__ import annotations

# Consola web de EstateHub SQL. Reglas de seguridad (STANDARDS sección 6):
# - Sin CDN ni fuentes externas: CSS y JS en línea, autorizados por un nonce por petición.
# - Sin manejadores en línea (onclick): los eventos se registran con addEventListener.
# - Todo dato que viene del servidor o del usuario se pinta con textContent, nunca con innerHTML.

_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>EstateHub SQL - Consola</title>
  <style nonce="__NONCE__">
    :root {
      --bg: #FAF9F5; --surface: #FFFFFF; --muted-bg: #F4F4F5; --code-bg: #F6F8FA;
      --ink: #18181B; --body: #3F3F46; --muted: #71717A; --line: #E4E4E7;
      --teal: #0F766E; --teal-bg: #F0FDFA; --teal-line: #99F6E4;
      --amber: #92400E; --amber-bg: #FFFBEB; --amber-line: #FCD34D;
      --red: #B91C1C; --red-bg: #FEF2F2; --red-line: #FCA5A5;
      --green: #047857; --green-bg: #ECFDF5; --green-line: #6EE7B7;
      --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 14px; }
    header { background: var(--surface); border-bottom: 1px solid var(--line); position: sticky; top: 0; z-index: 5; }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px; }
    .top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; }
    .brand { display: flex; align-items: center; gap: 10px; }
    .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--teal); }
    .brand strong { font-size: 18px; }
    .chip { font-family: var(--mono); font-size: 11px; padding: 2px 8px; border-radius: 6px;
      background: var(--teal-bg); color: var(--teal); border: 1px solid var(--teal-line); }
    .sub { color: var(--muted); font-size: 12px; margin: 2px 0 0; }
    a.link { font-family: var(--mono); font-size: 12px; color: var(--ink); text-decoration: none;
      border: 1px solid var(--line); background: var(--muted-bg); padding: 6px 10px; border-radius: 8px; }
    [role=tablist] { display: flex; gap: 22px; border-top: 1px solid var(--line); }
    [role=tab] { background: none; border: none; border-bottom: 2px solid transparent; padding: 11px 2px;
      font: inherit; color: var(--body); cursor: pointer; }
    [role=tab][aria-selected=true] { border-bottom-color: var(--teal); color: var(--teal); font-weight: 600; }
    [role=tab]:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {
      outline: 2px solid var(--teal); outline-offset: 2px; }
    main { padding: 22px 0 40px; }
    .banner { border-radius: 10px; border: 1px solid var(--line); padding: 12px 14px; margin-bottom: 16px; }
    .banner[hidden] { display: none; }
    .banner.ok { background: var(--green-bg); border-color: var(--green-line); color: #064E3B; }
    .banner.warn { background: var(--amber-bg); border-color: var(--amber-line); color: #78350F; }
    .banner.err { background: var(--red-bg); border-color: var(--red-line); color: #7F1D1D; }
    .banner .t { font-weight: 600; }
    .banner .d { font-family: var(--mono); font-size: 12px; margin-top: 3px; word-break: break-word; }
    .grid { display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
    .card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
    .card + .card { margin-top: 16px; }
    .grid > .card { margin-top: 0; }
    .grid.wide { grid-template-columns: 430px 1fr; }
    input.mono { font-family: var(--mono); font-size: 13px; }
    button.ghost.block { display: block; width: 100%; margin-top: 8px; }
    .card h2 { font-size: 15px; margin: 0; }
    .card .hint { color: var(--muted); font-size: 12px; margin: 2px 0 12px; font-family: var(--mono); }
    label { display: block; font-size: 12px; font-weight: 500; color: var(--body); margin: 10px 0 4px; }
    input, select { width: 100%; padding: 8px 10px; border: 1px solid #D4D4D8; border-radius: 8px;
      font: inherit; background: #FFFFFF; color: var(--ink); }
    .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
    button.primary, button.dark, button.ghost, button.warnbtn, button.danger {
      font: inherit; border-radius: 8px; padding: 9px 12px; cursor: pointer; border: 1px solid transparent; }
    button.primary { background: var(--teal); color: #FFFFFF; width: 100%; margin-top: 14px; font-weight: 600; }
    button.dark { background: #FFFFFF; border-color: #27272A; color: #27272A; width: 100%; margin-top: 14px; font-weight: 600; }
    button.ghost { background: var(--muted-bg); border-color: var(--line); color: var(--ink); font-size: 12px; padding: 6px 10px; }
    button.warnbtn { background: var(--amber-bg); border-color: var(--amber-line); color: var(--amber); width: 100%; margin-top: 8px; font-size: 12px; }
    button.danger { background: #FFFFFF; border-color: var(--red-line); color: var(--red); font-size: 12px; padding: 6px 10px; }
    button:disabled { opacity: .45; cursor: default; }
    .results-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px;
      border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 14px; }
    .summary { font-family: var(--mono); font-size: 12px; color: var(--muted); margin: 2px 0 0; }
    .pager { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 12px; }
    .props { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .prop { border: 1px solid var(--line); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
    .prop .meta { display: flex; justify-content: space-between; align-items: center; }
    .prop .city { font-family: var(--mono); font-size: 12px; color: var(--teal); font-weight: 600; }
    .prop h3 { font-size: 14px; margin: 4px 0 2px; }
    .prop .ag { color: var(--muted); font-size: 12px; margin: 0; }
    .prop .foot { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--line); padding-top: 10px; }
    .price { font-family: var(--mono); font-weight: 700; font-size: 15px; }
    .status { font-family: var(--mono); font-size: 11px; padding: 2px 7px; border-radius: 6px; border: 1px solid var(--line); }
    .status.available { background: var(--green-bg); color: var(--green); border-color: var(--green-line); }
    .status.reserved { background: var(--amber-bg); color: var(--amber); border-color: var(--amber-line); }
    .status.sold { background: var(--red-bg); color: var(--red); border-color: var(--red-line); }
    .empty { border: 1px dashed #D4D4D8; border-radius: 12px; padding: 22px; text-align: center; color: var(--muted); }
    .visit { border: 1px solid var(--line); background: #FCFCFB; border-radius: 12px; padding: 12px 14px;
      display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .visit + .visit { margin-top: 10px; }
    .visit .id { font-family: var(--mono); font-size: 12px; font-weight: 700; background: var(--teal-bg); color: var(--teal);
      padding: 2px 7px; border-radius: 6px; margin-right: 6px; }
    .visit .who { font-weight: 600; }
    .visit .mail, .visit .when { font-family: var(--mono); font-size: 12px; color: var(--muted); }
    .visit .when { color: var(--body); margin-top: 4px; }
    .visit .notes { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .actions { display: flex; flex-direction: column; gap: 6px; min-width: 120px; }
    .note { font-size: 12px; color: var(--amber); background: var(--amber-bg); border: 1px solid var(--amber-line);
      border-radius: 8px; padding: 8px 10px; margin-top: 12px; }
    .preset { display: block; width: 100%; text-align: left; background: var(--code-bg); border: 1px solid var(--line);
      border-radius: 10px; padding: 10px 12px; margin-top: 8px; cursor: pointer; font: inherit; color: var(--ink); }
    .preset .m { font-family: var(--mono); font-size: 12px; font-weight: 700; }
    .preset .x { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .reqline { font-family: var(--mono); font-size: 12px; font-weight: 600; }
    .badge { font-family: var(--mono); font-size: 12px; padding: 2px 8px; border-radius: 6px; background: var(--muted-bg); }
    .badge.ok { background: var(--green-bg); color: var(--green); }
    .badge.warn { background: var(--amber-bg); color: var(--amber); }
    .badge.err { background: var(--red-bg); color: var(--red); }
    pre { background: var(--code-bg); color: var(--ink); border: 1px solid var(--line); border-radius: 10px;
      padding: 14px; font-family: var(--mono); font-size: 12px; min-height: 260px; overflow-x: auto; margin: 12px 0 0; }
    [hidden] { display: none !important; }
    @media (max-width: 900px) { .grid, .grid.wide, .props { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="top">
        <div class="brand">
          <span class="dot" aria-hidden="true"></span>
          <div>
            <strong>EstateHub SQL</strong> <span class="chip">SQLModel + Repository</span>
            <p class="sub">Catálogo inmobiliario relacional, filtros paginados y agenda sin colisiones</p>
          </div>
        </div>
        <a class="link" href="/docs" target="_blank" rel="noopener">Contrato OpenAPI (/docs)</a>
      </div>
      <div role="tablist" aria-label="Secciones de la consola">
        <button role="tab" id="tab-catalog" aria-selected="true" aria-controls="panel-catalog" data-tab="catalog">1. Catálogo y filtros SQL</button>
        <button role="tab" id="tab-visits" aria-selected="false" aria-controls="panel-visits" data-tab="visits" tabindex="-1">2. Agenda de visitas</button>
        <button role="tab" id="tab-playground" aria-selected="false" aria-controls="panel-playground" data-tab="playground" tabindex="-1">3. Pruebas HTTP</button>
      </div>
    </div>
  </header>

  <main class="wrap">
    <div id="banner" class="banner" role="status" aria-live="polite" hidden>
      <div class="t" id="banner-title"></div>
      <div class="d" id="banner-detail"></div>
    </div>

    <section id="panel-catalog" role="tabpanel" aria-labelledby="tab-catalog">
      <div class="grid">
        <div>
          <div class="card">
            <h2>Filtros dinámicos</h2>
            <p class="hint">GET /api/v1/properties</p>
            <label for="f-city">Ciudad (sin distinguir mayúsculas)</label>
            <input id="f-city" type="text" placeholder="Antigua" />
            <div class="row2">
              <div><label for="f-min">Precio mínimo (USD)</label><input id="f-min" type="number" min="0" step="10000" /></div>
              <div><label for="f-max">Precio máximo (USD)</label><input id="f-max" type="number" min="0" step="10000" /></div>
            </div>
            <div class="row3">
              <div><label for="f-beds">Habitaciones</label>
                <select id="f-beds"><option value="">Todas</option><option value="2">2 o más</option><option value="3">3 o más</option><option value="4">4 o más</option></select></div>
              <div><label for="f-status">Estado</label>
                <select id="f-status"><option value="">Todos</option><option value="available">Disponible</option><option value="reserved">Reservada</option><option value="sold">Vendida</option></select></div>
              <div><label for="f-size">Por página</label>
                <select id="f-size"><option value="4">4</option><option value="10" selected>10</option></select></div>
            </div>
            <button class="primary" id="btn-apply" type="button">Ejecutar consulta paginada</button>
            <button class="ghost block" id="btn-reset" type="button">Limpiar filtros</button>
          </div>
          <div class="card">
            <h2>Registrar propiedad</h2>
            <p class="hint">POST /api/v1/properties (valida la FK agency_id)</p>
            <label for="p-agency">Agencia</label><select id="p-agency"></select>
            <label for="p-title">Título</label><input id="p-title" type="text" value="Townhouse Jardines de Antigua" />
            <div class="row3">
              <div><label for="p-city">Ciudad</label><input id="p-city" type="text" value="Antigua" /></div>
              <div><label for="p-price">Precio</label><input id="p-price" type="number" value="315000" /></div>
              <div><label for="p-beds">Hab.</label><input id="p-beds" type="number" value="3" min="1" max="20" /></div>
            </div>
            <button class="dark" id="btn-create-prop" type="button">Guardar propiedad</button>
          </div>
        </div>
        <div class="card">
          <div class="results-head">
            <div><h2>Resultados del catálogo</h2><p class="summary" id="summary">Cargando...</p></div>
            <div class="pager">
              <button class="ghost" id="btn-prev" type="button">Anterior</button>
              <span id="page-label">Página 1 de 1</span>
              <button class="ghost" id="btn-next" type="button">Siguiente</button>
            </div>
          </div>
          <div id="props" class="props"></div>
        </div>
      </div>
    </section>

    <section id="panel-visits" role="tabpanel" aria-labelledby="tab-visits" hidden>
      <div class="grid wide">
        <div class="card">
          <h2>Agendar visita</h2>
          <p class="hint">POST /api/v1/properties/{id}/visits</p>
          <label for="v-prop">Propiedad</label><select id="v-prop"></select>
          <div class="row2">
            <div><label for="v-name">Nombre</label><input id="v-name" type="text" value="Carlos Estrada" /></div>
            <div><label for="v-email">Correo</label><input id="v-email" type="email" value="carlos@ejemplo.example" /></div>
          </div>
          <div class="row2">
            <div><label for="v-start">Inicio (ISO 8601)</label><input id="v-start" class="mono" type="text" value="2027-05-15T14:00:00Z" /></div>
            <div><label for="v-end">Fin (ISO 8601)</label><input id="v-end" class="mono" type="text" value="2027-05-15T15:00:00Z" /></div>
          </div>
          <label for="v-notes">Notas</label><input id="v-notes" type="text" value="Revisión de planos y parqueo." />
          <button class="primary" id="btn-schedule" type="button">Confirmar visita</button>
          <button class="warnbtn" id="btn-overlap" type="button">Probar horario traslapado (10:30 a 11:30, espera 409)</button>
        </div>
        <div class="card">
          <div class="results-head">
            <div><h2>Visitas registradas</h2><p class="summary">Intervalos [inicio, fin) en UTC, ordenados por inicio</p></div>
            <button class="ghost" id="btn-refresh" type="button">Refrescar</button>
          </div>
          <div id="visits"></div>
          <p class="note">Esta API aún no tiene autenticación: cualquiera puede cancelar o mover visitas y por eso el correo se muestra enmascarado. Se protege en la Unidad 3.</p>
        </div>
      </div>
    </section>

    <section id="panel-playground" role="tabpanel" aria-labelledby="tab-playground" hidden>
      <div class="grid">
        <div class="card">
          <h2>Escenarios HTTP</h2>
          <p class="hint">Peticiones directas para observar código de estado y JSON</p>
          <button class="preset" type="button" data-preset="filter"><div class="m">GET /api/v1/properties?city=antigua&amp;min_bedrooms=2</div><div class="x">Filtro con JOIN de agencia y paginación (200)</div></button>
          <button class="preset" type="button" data-preset="conflict"><div class="m">POST /api/v1/properties/1/visits</div><div class="x">Traslape con la visita de 10:00 a 11:00 (409)</div></button>
          <button class="preset" type="button" data-preset="invalid"><div class="m">POST /api/v1/properties/1/visits</div><div class="x">Fin antes que inicio (422 VALIDATION_ERROR)</div></button>
          <button class="preset" type="button" data-preset="patch"><div class="m">PATCH /api/v1/properties/1/visits/1</div><div class="x">Reprogramar con cuerpo vacío (422)</div></button>
          <button class="preset" type="button" data-preset="agenda"><div class="m">GET /api/v1/agencies/1/visits?from=...&amp;to=...</div><div class="x">Agenda de una agencia en un rango (reto, parte 2)</div></button>
          <button class="preset" type="button" data-preset="delete404"><div class="m">DELETE /api/v1/properties/1/visits/9999</div><div class="x">Visita inexistente (404 VISIT_NOT_FOUND)</div></button>
        </div>
        <div class="card">
          <div class="results-head">
            <span class="reqline" id="pg-line">Elige un escenario</span>
            <span class="badge" id="pg-badge">HTTP ---</span>
          </div>
          <pre id="pg-body">La respuesta JSON aparecerá aquí.</pre>
        </div>
      </div>
    </section>
  </main>

  <script nonce="__NONCE__">
    'use strict';
    const $ = (id) => document.getElementById(id);
    const state = { page: 1, pages: 1 };
    const STATUS_LABELS = { available: 'Disponible', reserved: 'Reservada', sold: 'Vendida' };

    function el(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined && text !== null) node.textContent = String(text);
      return node;
    }

    function showBanner(kind, title, detail) {
      const box = $('banner');
      box.className = 'banner ' + kind;
      $('banner-title').textContent = title;
      $('banner-detail').textContent = detail || '';
      box.hidden = false;
    }

    async function api(method, url, payload) {
      const opts = { method, headers: {} };
      if (payload !== undefined) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(payload);
      }
      const res = await fetch(url, opts);
      const text = await res.text();
      let body = null;
      try { body = text ? JSON.parse(text) : null; } catch (_e) { body = text; }
      return { res, body };
    }

    function errorText(body) {
      if (body && body.error) return body.error.code + ' - ' + body.error.message;
      return JSON.stringify(body);
    }

    function selectTab(name) {
      document.querySelectorAll('[role=tab]').forEach((tab) => {
        const active = tab.dataset.tab === name;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        $('panel-' + tab.dataset.tab).hidden = !active;
      });
      $('banner').hidden = true;
      if (name === 'visits') loadVisits();
    }

    function fillSelect(select, items, label) {
      const previous = select.value;
      select.replaceChildren();
      items.forEach((item) => {
        const opt = el('option', null, label(item));
        opt.value = String(item.id);
        select.appendChild(opt);
      });
      if (previous && items.some((i) => String(i.id) === previous)) select.value = previous;
    }

    async function loadAgencies() {
      const { res, body } = await api('GET', '/api/v1/agencies');
      if (res.ok) fillSelect($('p-agency'), body, (a) => a.name + ' (ID ' + a.id + ')');
    }

    function propertyCard(p) {
      const card = el('article', 'prop');
      const head = el('div');
      const line = el('div', 'meta');
      line.appendChild(el('span', 'city', p.city));
      line.appendChild(el('span', 'status ' + p.status, STATUS_LABELS[p.status] || p.status));
      head.appendChild(line);
      head.appendChild(el('h3', null, p.title));
      head.appendChild(el('p', 'ag', 'Agencia ' + p.agency_name + ' (FK ' + p.agency_id + ')'));
      const foot = el('div', 'foot');
      foot.appendChild(el('span', 'price', '$' + Number(p.price).toLocaleString('en-US') + ' · ' + p.bedrooms + ' hab.'));
      const btn = el('button', 'ghost', 'Ver agenda');
      btn.type = 'button';
      btn.addEventListener('click', () => { $('v-prop').value = String(p.id); selectTab('visits'); });
      foot.appendChild(btn);
      card.appendChild(head);
      card.appendChild(foot);
      return card;
    }

    async function applyFilters(page) {
      state.page = page;
      const params = new URLSearchParams();
      const city = $('f-city').value.trim();
      if (city) params.set('city', city);
      if ($('f-min').value) params.set('min_price', $('f-min').value);
      if ($('f-max').value) params.set('max_price', $('f-max').value);
      if ($('f-beds').value) params.set('min_bedrooms', $('f-beds').value);
      if ($('f-status').value) params.set('status', $('f-status').value);
      params.set('page', String(page));
      params.set('size', $('f-size').value);
      const url = '/api/v1/properties?' + params.toString();
      const { res, body } = await api('GET', url);
      if (!res.ok) { showBanner('err', 'Error HTTP ' + res.status + ' en ' + url, errorText(body)); return; }
      state.pages = Math.max(1, body.pages);
      $('summary').textContent = 'GET ' + url + ' -> ' + body.total + ' inmuebles (mostrando ' + body.items.length + ')';
      $('page-label').textContent = 'Página ' + body.page + ' de ' + state.pages;
      $('btn-prev').disabled = body.page <= 1;
      $('btn-next').disabled = body.page >= state.pages;
      const grid = $('props');
      grid.replaceChildren();
      if (body.items.length === 0) {
        grid.appendChild(el('div', 'empty', 'Ninguna propiedad coincide con los filtros.'));
      } else {
        body.items.forEach((p) => grid.appendChild(propertyCard(p)));
      }
      if (body.items.length > 0) {
        fillSelect($('v-prop'), body.items, (p) => '#' + p.id + ' ' + p.title + ' (' + p.city + ')');
      }
    }

    async function createProperty() {
      const payload = {
        agency_id: Number($('p-agency').value),
        title: $('p-title').value,
        city: $('p-city').value,
        price: Number($('p-price').value),
        bedrooms: Number($('p-beds').value),
        status: 'available'
      };
      const { res, body } = await api('POST', '/api/v1/properties', payload);
      if (!res.ok) { showBanner('err', 'Error HTTP ' + res.status + ' al crear la propiedad', errorText(body)); return; }
      showBanner('ok', 'Propiedad creada (201, ID ' + body.id + ')', body.title + ' en ' + body.city);
      applyFilters(1);
    }

    function shiftIso(iso, minutes) {
      return new Date(new Date(iso).getTime() + minutes * 60000).toISOString().replace('.000Z', 'Z');
    }

    function visitRow(v) {
      const row = el('div', 'visit');
      const info = el('div');
      const who = el('div');
      who.appendChild(el('span', 'id', 'Visita ' + v.id));
      who.appendChild(el('span', 'who', v.visitor_name + ' '));
      who.appendChild(el('span', 'mail', '(' + v.visitor_email_masked + ')'));
      info.appendChild(who);
      info.appendChild(el('div', 'when', v.scheduled_start + ' -> ' + v.scheduled_end));
      if (v.notes) info.appendChild(el('div', 'notes', v.notes));
      const actions = el('div', 'actions');
      const move = el('button', 'ghost', 'Mover 30 min (PATCH)');
      move.type = 'button';
      move.addEventListener('click', () => rescheduleVisit(v));
      const cancel = el('button', 'danger', 'Cancelar (DELETE)');
      cancel.type = 'button';
      cancel.addEventListener('click', () => cancelVisit(v.property_id, v.id));
      actions.appendChild(move);
      actions.appendChild(cancel);
      row.appendChild(info);
      row.appendChild(actions);
      return row;
    }

    async function loadVisits() {
      const propId = $('v-prop').value;
      const box = $('visits');
      box.replaceChildren();
      if (!propId) { box.appendChild(el('div', 'empty', 'No hay propiedades cargadas.')); return; }
      const { res, body } = await api('GET', '/api/v1/properties/' + encodeURIComponent(propId) + '/visits');
      if (!res.ok) { box.appendChild(el('div', 'empty', 'No se pudieron cargar las visitas.')); return; }
      if (body.length === 0) { box.appendChild(el('div', 'empty', 'Sin visitas agendadas: el horario está libre.')); return; }
      body.forEach((v) => box.appendChild(visitRow(v)));
    }

    async function scheduleVisit() {
      const propId = $('v-prop').value || '1';
      const payload = {
        visitor_name: $('v-name').value,
        visitor_email: $('v-email').value,
        scheduled_start: $('v-start').value,
        scheduled_end: $('v-end').value,
        notes: $('v-notes').value
      };
      const { res, body } = await api('POST', '/api/v1/properties/' + encodeURIComponent(propId) + '/visits', payload);
      if (res.status === 409) showBanner('warn', 'Conflicto (409)', errorText(body));
      else if (!res.ok) showBanner('err', 'Error HTTP ' + res.status, errorText(body));
      else showBanner('ok', 'Visita agendada (201, ID ' + body.id + ')', body.scheduled_start + ' -> ' + body.scheduled_end);
      loadVisits();
    }

    async function rescheduleVisit(v) {
      const payload = { scheduled_start: shiftIso(v.scheduled_start, 30), scheduled_end: shiftIso(v.scheduled_end, 30) };
      const url = '/api/v1/properties/' + v.property_id + '/visits/' + v.id;
      const { res, body } = await api('PATCH', url, payload);
      if (res.ok) showBanner('ok', 'Visita ' + v.id + ' reprogramada (200)', body.scheduled_start + ' -> ' + body.scheduled_end);
      else showBanner(res.status === 409 ? 'warn' : 'err', 'PATCH respondió ' + res.status, errorText(body));
      loadVisits();
    }

    async function cancelVisit(propId, visitId) {
      const { res, body } = await api('DELETE', '/api/v1/properties/' + propId + '/visits/' + visitId);
      if (res.status === 204) showBanner('ok', 'Visita ' + visitId + ' cancelada (204)', 'El bloque horario quedó libre.');
      else showBanner('err', 'Error HTTP ' + res.status, errorText(body));
      loadVisits();
    }

    const PRESETS = {
      filter: ['GET', '/api/v1/properties?city=antigua&min_bedrooms=2&page=1&size=5'],
      conflict: ['POST', '/api/v1/properties/1/visits', {
        visitor_name: 'Andrea Morales', visitor_email: 'andrea@ejemplo.example',
        scheduled_start: '2027-05-15T10:30:00Z', scheduled_end: '2027-05-15T11:30:00Z' }],
      invalid: ['POST', '/api/v1/properties/1/visits', {
        visitor_name: 'Andrea Morales', visitor_email: 'andrea@ejemplo.example',
        scheduled_start: '2027-05-15T16:00:00Z', scheduled_end: '2027-05-15T15:00:00Z' }],
      patch: ['PATCH', '/api/v1/properties/1/visits/1', {}],
      agenda: ['GET', '/api/v1/agencies/1/visits?from=2027-05-15T00:00:00Z&to=2027-05-16T00:00:00Z'],
      delete404: ['DELETE', '/api/v1/properties/1/visits/9999']
    };

    async function runPreset(name) {
      const [method, url, payload] = PRESETS[name];
      $('pg-line').textContent = method + ' ' + url;
      const { res, body } = await api(method, url, payload);
      const badge = $('pg-badge');
      badge.textContent = 'HTTP ' + res.status;
      badge.className = 'badge ' + (res.ok ? 'ok' : (res.status === 409 ? 'warn' : 'err'));
      $('pg-body').textContent = body === null ? '(sin cuerpo)' : JSON.stringify(body, null, 2);
    }

    document.querySelectorAll('[role=tab]').forEach((tab) => {
      tab.addEventListener('click', () => selectTab(tab.dataset.tab));
      tab.addEventListener('keydown', (ev) => {
        if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
        const tabs = Array.from(document.querySelectorAll('[role=tab]'));
        const i = tabs.indexOf(tab) + (ev.key === 'ArrowRight' ? 1 : -1);
        const next = tabs[(i + tabs.length) % tabs.length];
        next.focus();
        selectTab(next.dataset.tab);
      });
    });
    document.querySelectorAll('[data-preset]').forEach((b) => b.addEventListener('click', () => runPreset(b.dataset.preset)));
    $('btn-apply').addEventListener('click', () => applyFilters(1));
    $('btn-reset').addEventListener('click', () => {
      ['f-city', 'f-min', 'f-max', 'f-beds', 'f-status'].forEach((id) => { $(id).value = ''; });
      applyFilters(1);
    });
    $('btn-prev').addEventListener('click', () => { if (state.page > 1) applyFilters(state.page - 1); });
    $('btn-next').addEventListener('click', () => { if (state.page < state.pages) applyFilters(state.page + 1); });
    $('btn-create-prop').addEventListener('click', createProperty);
    $('btn-schedule').addEventListener('click', scheduleVisit);
    $('btn-overlap').addEventListener('click', () => {
      $('v-start').value = '2027-05-15T10:30:00Z';
      $('v-end').value = '2027-05-15T11:30:00Z';
      scheduleVisit();
    });
    $('btn-refresh').addEventListener('click', loadVisits);
    $('v-prop').addEventListener('change', loadVisits);

    loadAgencies().then(() => applyFilters(1));
  </script>
</body>
</html>"""


def render_console_html(nonce: str) -> str:
    """Devuelve la consola en modo claro con el nonce de CSP de esta petición."""
    return _TEMPLATE.replace("__NONCE__", nonce)
