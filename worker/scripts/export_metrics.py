#!/usr/bin/env python3
"""
Export worker processing metrics to CSV/JSON from JSONL log produced by worker.
Usage:
  python worker/scripts/export_metrics.py --log-dir /tmp/metrics --out metrics_export
This will create:
  metrics_export.csv and metrics_export.json with normalized rows
  metrics_export.summary.json with aggregates
"""
import os
import json
import csv
import argparse
from statistics import mean


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def normalize_row(r):
    return {
        'job_id': r.get('job_id'),
        'status': r.get('status'),
        'mode': r.get('mode'),
        'analyze_s': r.get('analyze_s', 0.0),
        'invert_s': r.get('invert_s', 0.0),
        'render_s': r.get('render_s', 0.0),
        'total_s': r.get('total_s', 0.0),
        'timestamp': r.get('timestamp'),
        'error': r.get('error', ''),
    }


def export(rows, out_base):
    norm = [normalize_row(r) for r in rows]
    # csv
    csv_path = out_base + '.csv'
    if norm:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(norm[0].keys()))
            w.writeheader()
            for r in norm:
                w.writerow(r)
    # json
    with open(out_base + '.json', 'w', encoding='utf-8') as f:
        json.dump(norm, f, ensure_ascii=False, indent=2)
    # summary
    if norm:
        totals = [r['total_s'] for r in norm if r['total_s']]
        analyze = [r['analyze_s'] for r in norm if r['analyze_s']]
        invert = [r['invert_s'] for r in norm if r['invert_s']]
        render = [r['render_s'] for r in norm if r['render_s']]
        completed = sum(1 for r in norm if r['status'] == 'COMPLETED')
        failed = sum(1 for r in norm if r['status'] == 'FAILED')
        summary = {
            'count': len(norm),
            'completed': completed,
            'failed': failed,
            'p50_total_s': sorted(totals)[len(totals)//2] if totals else 0,
            'avg_total_s': round(mean(totals), 3) if totals else 0,
            'avg_analyze_s': round(mean(analyze), 3) if analyze else 0,
            'avg_invert_s': round(mean(invert), 3) if invert else 0,
            'avg_render_s': round(mean(render), 3) if render else 0,
        }
        with open(out_base + '.summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log-dir', default=os.getenv('METRICS_LOG_DIR', '/tmp/metrics'))
    ap.add_argument('--out', default='metrics_export')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    path = os.path.join(args.log_dir, 'processing_metrics.jsonl')
    rows = load_jsonl(path)
    export(rows, args.out)
    print(f'Exported {len(rows)} rows to {args.out}.csv/.json and summary to {args.out}.summary.json')


if __name__ == '__main__':
    main()

