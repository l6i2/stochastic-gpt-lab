"""Ecuador-first time report. No market calls, orders, datasets or clock repair."""
import argparse
from datetime import date, datetime, timezone
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from time_semantics import (ECUADOR, DISPLAY_COLUMNS, instant_display,
    new_york_reference_session, new_york_dst_changes)


def build(day):
    observation = json.loads((ROOT / 'configs/pc_a_remaining_blockers_evidence_20261028/current_server_native_sessions.json').read_text())
    return dict(primary_timezone='America/Guayaquil',
        receipt=instant_display(datetime.now(timezone.utc), basis='HOST_RECEIPT_UNATTESTED'),
        session=new_york_reference_session(day), dst=new_york_dst_changes(day.year),
        xm_native_sessions=observation, XM_SERVER_MAPPING='PARTIAL_NO_AUTHORIZED_PERIODS',
        UTC_CAUSAL_CERTIFICATION='BLOCKED', CAUSAL_AUDIT='FAIL',
        DISCOVERY_VALIDATION='BLOCKED', FINAL_TEST='LOCKED', DEMO='DISABLED', LIVE_TRADING=False)


def render(report):
    esc = lambda value: html.escape(str(value))
    rows = [('Recepción local (reloj no certificado)', report['receipt']),
            ('Referencia NY: inicio nominal', report['session']['start']),
            ('Referencia NY: fin nominal', report['session']['end'])]
    table = '<table><tr><th>Referencia</th>' + ''.join('<th>'+c+'</th>' for c in DISPLAY_COLUMNS) + '</tr>'
    for label, view in rows:
        table += '<tr><th>'+esc(label)+'</th>'+''.join('<td>'+esc(view[c] or 'No verificado')+'</td>' for c in DISPLAY_COLUMNS)+'</tr>'
    table += '</table>'
    changes = ''.join('<li>'+esc(row['transition']['Ecuador'])+' Ecuador · Nueva York '+esc(row['transition']['new_york_abbreviation'])+'</li>' for row in report['dst'])
    sessions = '\n'.join(r for r in report['xm_native_sessions']['canonical_observation']['records'] if '|QUOTE|' in r or '|TRADE|' in r)
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Horario Ecuador · Stochastic-GPT-Lab</title><style>body{font:16px system-ui;margin:3em;background:#101c28;color:#edf4fa}table{border-collapse:collapse;width:100%}td,th{padding:14px;border:1px solid #526476;text-align:left}th:nth-child(2),td:nth-child(2){background:#174a45}pre{white-space:pre-wrap}p{max-width:1000px;line-height:1.6}</style><h1>Horario principal: Ecuador</h1><p>America/Guayaquil · '+esc(report['session']['date'])+'</p>'+table+'<p>Referencia nominal NYSE. No certifica días hábiles, feriados, cierres anticipados ni apertura de US30Cash. El horario específico XM sigue sin mapping UTC autorizado.</p><h2>Cambios de horario de Nueva York</h2><ul>'+changes+'</ul><h2>Sesiones XM observadas, originales</h2><p>Etiquetas nativas; no se aplicó un offset supuesto. Excepciones históricas desconocidas.</p><pre>'+esc(sessions)+'</pre><p>Certificación causal BLOCKED · Auditoría FAIL · Discovery BLOCKED · Final Test LOCKED · DEMO DISABLED · LIVE_TRADING=false.</p></html>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=datetime.now(ECUADOR).date())
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/pc_a/time_display')
    args=parser.parse_args()
    report=build(args.date)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'time_report.json').write_bytes(json.dumps(report,indent=2,ensure_ascii=False).encode())
    (args.output/'time_report.html').write_bytes(render(report).encode())
    print(args.output/'time_report.html')


if __name__ == '__main__': main()
