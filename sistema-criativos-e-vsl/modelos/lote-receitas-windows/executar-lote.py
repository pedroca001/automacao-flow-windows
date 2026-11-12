"""Run the supplier queue, admitting only inputs with a checked local snapshot."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
sys.path.insert(0, str(BASE / 'retomada-macro'))
import noturno
import noturno_adapter
from noturno_core import Queue, read


class SyncQueue(Queue):
    def eligible(self):
        if read(self.root / 'BLOQUEIO-FLOW.json', {}).get('status') == 'active':
            # Continue read-only reconciliation/downloads; never submit through
            # the service's observed unusual-activity restriction.
            return []
        inventory = read(self.root / 'inventario-imagens.json', {})
        allowed = {'PAR-' + key for key, value in inventory.items()
                   if Path(value['file']).is_file() and Path(value['file']).stat().st_size == value['bytes']}
        original = self.plan
        # Keep the immutable complete plan/state. Only filter this scheduling
        # query; a not-yet-synced source remains pending and never fails upload.
        selected = [item for item in original['videos'] if item['id'] in allowed
                    or any(self.scenes[item['id'] + '_' + str(n)]['attempts'] for n in range(1, 5))]
        if not (self.root / 'PILOTOS-APROVADOS.json').exists():
            pilot_ids = {item['id'] for item in original['videos'][:3]}
            selected = [item for item in selected if item['id'] in pilot_ids]
        try:
            self.plan = {**original, 'videos': selected}
            return super().eligible()
        finally:
            self.plan = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validar', action='store_true')
    args = parser.parse_args()
    noturno.Queue = SyncQueue
    return noturno.execute(argparse.Namespace(plano=str(ROOT / 'plano-noturno.json'), validar=args.validar))


if __name__ == '__main__':
    raise SystemExit(main())
