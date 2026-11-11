import os
from collections import defaultdict
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import duckdb

TITLE = "Client Reporting"
TABLE = "crd_loans"
PORT = 8102
STYLE = """*{box-sizing:border-box}body{margin:0;color:#203342;background:#edf1f4;font:14px Arial,sans-serif}a{color:#11696c;text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #208fbb;outline-offset:3px}header{display:flex;align-items:center;gap:34px;background:#233a49;color:white;padding:18px 28px}.brand{color:white;font-size:20px;font-weight:bold;letter-spacing:-.5px}.brand span{font-weight:normal}.app{border-left:1px solid #637582;padding-left:28px;font-size:17px}.readonly{margin-left:auto;font-size:12px;color:#d1e0e7}nav{display:flex;align-items:center;justify-content:space-between;padding:10px 28px;background:white;border-bottom:1px solid #c9d3da}nav form{display:flex;align-items:center;gap:10px}nav label{font-size:12px}input,select,button{font:inherit;padding:9px 11px;border:1px solid #b9c7cf;border-radius:3px;background:white;color:inherit}button{background:#176d71;color:white;border-color:#176d71;cursor:pointer}main{max-width:1480px;margin:auto;padding:28px}h1{font-size:29px;letter-spacing:-.7px;margin:5px 0 8px}h2{font-size:20px;margin:0 0 8px}.context{color:#526675;margin:0;font-size:12px}.heading{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.count{font-size:13px;padding:8px 12px;border:1px solid #c5d1d8;background:#fff}.intro{color:#526675;line-height:1.6}section,.table-wrap{background:white}section{border:1px solid #cbd5dc}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap;font-size:13px}th{text-align:left;color:#4c6170;background:#e5ecf0;font-weight:normal;padding:12px 15px;border-bottom:1px solid #bac8d1}td{padding:11px 15px;border-bottom:1px solid #dbe3e8}tbody tr:nth-child(even){background:#f6f8fa}tbody tr:hover{background:#edf5f6}.number{text-align:right;font-variant-numeric:tabular-nums}.section-title{padding:15px 20px;font-weight:bold;border-bottom:1px solid #cbd5dc}.section-title span{float:right;font-weight:normal;font-size:12px;color:#526675}.empty{padding:45px;margin-top:20px}.portfolio{display:flex;justify-content:space-between;align-items:center;margin:30px 0 24px}.portfolio p{color:#526675}.total{text-align:right}.total span{display:block;color:#526675;margin-bottom:8px}.total strong{font-size:32px;font-weight:normal;font-variant-numeric:tabular-nums}footer{max-width:1480px;margin:25px auto;padding:0 28px 20px;font-size:11px;color:#5c707e}footer span{float:right}@media(max-width:700px){header{flex-wrap:wrap;gap:14px;padding:18px}.readonly{margin-left:0}.app{padding-left:14px}nav{align-items:start;gap:15px;flex-direction:column;padding:16px}nav form{flex-wrap:wrap}main{padding:18px}.portfolio{align-items:start;gap:18px;flex-direction:column}.total{text-align:left}footer span{display:block;float:none;margin-top:10px}}body{background:#f3f6fb;color:#192f50;font-size:15px}header{background:#142e53;padding:24px 44px}.brand{font-family:Georgia,serif;font-weight:normal;font-size:26px}.brand span{font-style:italic}.app{font-size:15px}.readonly{color:#c9d9ef}nav{padding:16px 44px}nav a,a{color:#225ba0}main{max-width:1280px;padding:40px 44px}h1{font-family:Georgia,serif;font-size:38px;font-weight:normal;letter-spacing:-1px}.context{font-size:13px;color:#536b8d}.heading{margin-bottom:32px}.intro{color:#536b8d}.count{border:0;background:#e1eaf7;color:#274b7b;border-radius:20px;padding:10px 18px}.section-title{padding:20px 24px;border-color:#dce4ef}section{border-color:#dce4ef;border-radius:8px;overflow:hidden}th{background:#edf2f8;color:#536b8d;border-color:#dce4ef;padding:15px 22px}td{padding:18px 22px;border-color:#e5ebf3}table{font-size:14px}tbody tr:nth-child(even){background:white}tbody tr:hover{background:#f3f7fd}button{background:#225ba0;border-color:#225ba0;border-radius:4px}.portfolio{padding:26px 0;border-top:1px solid #d7e0ed}.total strong{font-family:Georgia,serif;font-size:38px}footer{max-width:1280px;padding:0 44px 25px}@media(max-width:700px){header{padding:18px}nav{padding:16px}main{padding:24px 18px}h1{font-size:32px}footer{padding:0 18px 25px}}"""
LABELS = {
    "loan_id": "Loan ID", "client_id": "Client ID",
    "currency": "Currency", "balance": "Local balance", "balance_usd": "Balance USD",
    "product_name": "Product",
    "client_name": "Client", "rm_id": "RM", "segment": "Segment",
}


def esc(value):
    return escape(str(value), quote=True)


def money(value):
    return "—" if value is None else f"{value:,.2f}"


def link(kind, identifier):
    return f'<a href="/{kind}?id={quote(str(identifier), safe="")}">{esc(identifier)}</a>'


def page(title, body):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | {TITLE}</title><style>{STYLE}</style></head>
<body><header><a class="brand" href="/">Northhaven <span>Bank</span></a>
<div class="app">{TITLE}</div><span class="readonly">Read-only workspace</span></header>
<nav><a href="/">Client directory</a>
<form action="/loan" method="get"><label for="quick">Find a loan</label>
<input id="quick" name="id" placeholder="Loan ID, e.g. L0016" required>
<button>Open loan</button></form></nav>
<main>{body}</main><footer>Northhaven Bank · Fictional demonstration data
<span>Refresh the page to load the latest data</span></footer></body></html>"""


def holdings(rows):
    columns = ["loan_id", "product_name", "currency", "balance", "balance_usd", "rm_id", "segment"]
    header = "".join(f'<th scope="col">{LABELS[c]}</th>' for c in columns)
    body = ""
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            content = (link("loan", value) if col == "loan_id" else
                       esc(money(value)) if col in ("balance", "balance_usd") else esc(value))
            cls = ' class="number"' if col in ("balance", "balance_usd") else ""
            cells.append(f"<td{cls}>{content}</td>")
        body += "<tr>" + "".join(cells) + "</tr>"
    return f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>'


def empty():
    return '<section class="empty"><h2>No records found</h2><p>Check the identifier or adjust your filters.</p><a href="/">Return to the directory</a></section>'


def render_rows(url, rows):
    request = urlsplit(url)
    query = parse_qs(request.query)
    get = lambda key: query.get(key, [""])[0].strip()
    identifier = get("id")
    if request.path == "/loan":
        selected = [r for r in rows if r["loan_id"] == identifier]
        heading = f'<div class="heading"><div><p class="context">Loan record</p><h1>{esc(identifier)}</h1></div><a class="back" href="/">Back to directory</a></div>'
        if not selected:
            return 200, page(identifier, heading + empty())
        client = selected[0]
        body = heading + f'<p class="intro">{esc(client["client_name"])} / {link("client", client["client_id"])}</p><section><div class="section-title">Lending records <span>{len(selected)} rows</span></div>{holdings(selected)}</section>'
        return 200, page(identifier, body)
    if request.path == "/client":
        selected = [r for r in rows if r["client_id"] == identifier]
        name = selected[0].get("client_name", identifier) if selected else identifier
        body = f'<div class="heading"><div><p class="context">Client portfolio / {esc(identifier)}</p><h1>{esc(name)}</h1></div><a class="back" href="/">Back to directory</a></div>'
        if selected:
            total = sum(r["balance_usd"] for r in selected)
            body += f'<div class="portfolio"><div><h2>Lending holdings</h2><p>{len(selected)} rows · Values in account currency unless noted</p></div><div class="total"><span>Total USD</span><strong>{money(total)}</strong></div></div><section>{holdings(selected)}</section>'
        else:
            body += empty()
        return 200, page(name, body)
    if request.path != "/":
        return 404, page("Page not found", '<h1>Page not found</h1><a href="/">Return to the directory</a>')
    clients = defaultdict(list)
    for row in rows:
        clients[row["client_id"]].append(row)
    entries = ""
    for client_id, client_rows in sorted(clients.items()):
        entries += f'<tr><td>{link("client", client_id)}</td><td>{esc(client_rows[0]["client_name"])}</td><td>{esc(client_rows[0]["segment"])}</td><td class="number">{len(client_rows)}</td><td class="number">{money(sum(r["balance_usd"] for r in client_rows))}</td><td><a href="/client?id={quote(client_id, safe="")}">View holdings</a></td></tr>'
    body = f'<div class="heading"><div><p class="context">Relationship workspace</p><h1>Your clients</h1><p class="intro">Lending portfolios, ready for your next conversation.</p></div><span class="count">{len(clients)} clients</span></div>'
    body += f'<section><div class="section-title">Client directory <span>Lending portfolios</span></div><div class="table-wrap"><table><thead><tr><th>Client ID</th><th>Client</th><th>Segment</th><th>Rows</th><th>Total USD</th><th></th></tr></thead><tbody>{entries}</tbody></table></div></section>' if entries else empty()
    return 200, page(TITLE, body)


def render(url):
    path = Path(os.environ.get("RECON_DB", "~/lending-demo/lending.duckdb")).expanduser()
    try:
        with duckdb.connect(str(path), read_only=True) as db:
            result = db.execute(f"SELECT * FROM {TABLE} ORDER BY loan_id")
            columns = [c[0] for c in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
    except duckdb.Error:
        return 503, page("Data refreshing", '<section class="empty"><h1>Data refreshing</h1><p>Run the pipeline if data is not yet available, then refresh this page.</p><a href="/">Try again</a></section>')
    return render_rows(url, rows)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, html = render(self.path)
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        if status == 503:
            self.send_header("Retry-After", "3")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"{TITLE}: http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
