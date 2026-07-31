from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .exporters import export_csv_text, export_pdf_bytes
from .importers import records_from_csv_text
from .models import PERSON_FIELDS, PersonRecord
from .storage import PeopleStore


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>People Finder</title>
  <style>
    :root { color-scheme: light dark; font-family: Inter, system-ui, Segoe UI, sans-serif; }
    body { margin: 0; background: #10131a; color: #eef2ff; }
    main { max-width: 1120px; margin: 0 auto; padding: 32px 20px 64px; }
    h1 { margin-bottom: 4px; }
    .subtle { color: #aab3c5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    .card { background: #171b25; border: 1px solid #2a3142; border-radius: 18px; padding: 18px; box-shadow: 0 16px 60px #0004; }
    label { display: block; margin: 10px 0 4px; color: #c9d4ea; font-size: 13px; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #344058; background: #0d111a; color: #f8fafc; }
    textarea { min-height: 130px; resize: vertical; }
    button, .button { display: inline-block; border: 0; border-radius: 999px; padding: 10px 14px; margin-top: 12px; background: #8b5cf6; color: white; cursor: pointer; text-decoration: none; font-weight: 650; }
    button.secondary, .button.secondary { background: #293244; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border-bottom: 1px solid #2a3142; text-align: left; padding: 10px 8px; vertical-align: top; }
    th { color: #c9d4ea; }
    .notice { border-left: 4px solid #f59e0b; padding: 10px 12px; background: #2a2111; color: #fdecc8; border-radius: 12px; }
    .ok { color: #86efac; }
    .error { color: #fca5a5; }
  </style>
</head>
<body>
  <main>
    <h1>People Finder</h1>
    <p class="subtle">A local, privacy-first contact research workspace with CSV/PDF exports.</p>
    <p class="notice">Use consented or permitted sources only. This starter blocks high-risk private-person directory targets by default.</p>

    <div class="grid">
      <section class="card">
        <h2>Add person</h2>
        <form id="add-form">
          <label>Name *</label><input name="name" required />
          <label>Type</label>
          <select name="entity_type" style="width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #344058; background: #0d111a; color: #f8fafc;">
            <option value="person">Person</option>
            <option value="company">Company / företag</option>
          </select>
          <label>Role</label><input name="role" />
          <label>Organization</label><input name="organization" />
          <label>Postnummer / ZIP</label><input name="zip_code" />
          <label>Ort / city</label><input name="city" />
          <label>Country</label><input name="country" />
          <label>Email</label><input name="email" />
          <label>Phone</label><input name="phone" />
          <label>Profile URL</label><input name="profile_url" placeholder="https://example.com/profile" />
          <label>Source</label><input name="source" value="manual" />
          <label>Tags</label><input name="tags" placeholder="speaker, alumni, customer" />
          <label>Consent / lawful basis</label><input name="consent_basis" placeholder="consented, existing relationship, public professional page" />
          <label>Notes</label><textarea name="notes"></textarea>
          <button>Add record</button>
          <p id="add-status"></p>
        </form>
      </section>

      <section class="card">
        <h2>Import CSV</h2>
        <p class="subtle">Paste CSV with columns like: entity_type, name, role, organization, zip_code, city, country, email, phone, profile_url, source, notes, tags, consent_basis.</p>
        <textarea id="csv-text" placeholder="name,role,organization,city&#10;Ada Lovelace,Researcher,Example Lab,Stockholm"></textarea>
        <button id="import-button">Import</button>
        <p id="import-status"></p>
      </section>
    </div>

    <section class="card" style="margin-top: 16px;">
      <h2>Search & export</h2>
      <div class="row">
        <input id="query" placeholder="Search name, city, org, notes..." style="max-width: 420px;" />
        <button id="search-button" class="secondary">Search</button>
        <a id="csv-link" class="button" href="/export.csv">Download CSV</a>
        <a id="pdf-link" class="button" href="/export.pdf">Download PDF</a>
      </div>
      <div id="results"></div>
    </section>
  </main>
  <script>
    const fields = %FIELDS%;

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
    }

    async function loadRecords() {
      const query = document.getElementById('query').value;
      const params = new URLSearchParams({ query });
      document.getElementById('csv-link').href = '/export.csv?' + params;
      document.getElementById('pdf-link').href = '/export.pdf?' + params;
      const response = await fetch('/api/records?' + params);
      const records = await response.json();
      const rows = records.map(record => `
        <tr>
          <td>${escapeHtml(record.name)}<br><span class="subtle">${escapeHtml(record.entity_type)} · ${escapeHtml(record.tags)}</span></td>
          <td>${escapeHtml(record.role)}<br><span class="subtle">${escapeHtml(record.organization)}</span></td>
          <td>${escapeHtml([record.zip_code, record.city, record.country].filter(Boolean).join(', '))}</td>
          <td>${escapeHtml(record.email)}<br>${escapeHtml(record.phone)}</td>
          <td>${record.profile_url ? `<a href="${escapeHtml(record.profile_url)}" target="_blank">profile</a>` : ''}<br><span class="subtle">${escapeHtml(record.source)}</span></td>
        </tr>
      `).join('');
      document.getElementById('results').innerHTML = `
        <p class="subtle">${records.length} record(s)</p>
        <table>
          <thead><tr><th>Name</th><th>Work</th><th>Location</th><th>Contact</th><th>Source</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5">No records yet.</td></tr>'}</tbody>
        </table>
      `;
    }

    document.getElementById('add-form').addEventListener('submit', async event => {
      event.preventDefault();
      const formData = new FormData(event.target);
      const payload = Object.fromEntries(fields.map(field => [field, formData.get(field) || '']));
      const status = document.getElementById('add-status');
      const response = await fetch('/api/records', { method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(payload) });
      const body = await response.json();
      status.className = response.ok ? 'ok' : 'error';
      status.textContent = response.ok ? `Added record #${body.id}` : body.error;
      if (response.ok) {
        event.target.reset();
        event.target.elements.source.value = 'manual';
        loadRecords();
      }
    });

    document.getElementById('import-button').addEventListener('click', async () => {
      const status = document.getElementById('import-status');
      const response = await fetch('/api/import-csv', { method: 'POST', headers: {'content-type': 'text/csv'}, body: document.getElementById('csv-text').value });
      const body = await response.json();
      status.className = response.ok ? 'ok' : 'error';
      status.textContent = response.ok ? `Imported ${body.count} record(s)` : body.error;
      if (response.ok) loadRecords();
    });

    document.getElementById('search-button').addEventListener('click', loadRecords);
    document.getElementById('query').addEventListener('keydown', event => {
      if (event.key === 'Enter') loadRecords();
    });
    loadRecords();
  </script>
</body>
</html>
""".replace("%FIELDS%", json.dumps(PERSON_FIELDS))


class PeopleFinderHandler(BaseHTTPRequestHandler):
    store: PeopleStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query).get("query", [""])[0]

        if parsed.path == "/":
            self._send_text(INDEX_HTML, content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/api/records":
            records = [record.as_dict() for record in self.store.search(query=query)]
            self._send_json(records)
            return

        if parsed.path == "/export.csv":
            records = self.store.search(query=query)
            self._send_bytes(
                export_csv_text(records).encode("utf-8"),
                content_type="text/csv; charset=utf-8",
                filename="people.csv",
            )
            return

        if parsed.path == "/export.pdf":
            records = self.store.search(query=query)
            self._send_bytes(
                export_pdf_bytes(records),
                content_type="application/pdf",
                filename="people.pdf",
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/records":
                payload = json.loads(self._read_body().decode("utf-8"))
                record = PersonRecord.from_mapping(payload)
                record_id = self.store.add(record)
                self._send_json({"id": record_id}, status=HTTPStatus.CREATED)
                return

            if self.path == "/api/import-csv":
                csv_text = self._read_body().decode("utf-8-sig")
                records = records_from_csv_text(csv_text)
                count = self.store.add_many(records)
                self._send_json({"count": count}, status=HTTPStatus.CREATED)
                return

            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _read_body(self) -> bytes:
        length = int(self.headers.get("content-length", "0"))
        return self.rfile.read(length)

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(data, status=status, content_type="application/json; charset=utf-8")

    def _send_text(self, payload: str, status: HTTPStatus = HTTPStatus.OK, content_type: str = "text/plain; charset=utf-8") -> None:
        self._send_bytes(payload.encode("utf-8"), status=status, content_type=content_type)

    def _send_bytes(
        self,
        payload: bytes,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "application/octet-stream",
        filename: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        if filename:
            self.send_header("content-disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)


def run_server(db_path: str | Path = "data/people.db", host: str = "127.0.0.1", port: int = 8765) -> None:
    PeopleFinderHandler.store = PeopleStore(db_path)
    server = ThreadingHTTPServer((host, port), PeopleFinderHandler)
    print(f"People Finder running at http://{host}:{port}")
    server.serve_forever()
