"""Authorized 30-minute cooldown, project-tab refresh and receipt-safe resume."""
import copy
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
sys.path.insert(0, str(BASE / 'retomada-macro'))
from flow_platform import locks, macro_processes, process_options
from noturno_core import ALLOWED_MODELS, atomic, norm, read, redact, validate_plan
from noturno_adapter import Adapter

DELAY = 1800
CONTROLLER = ROOT / 'executar-lote.py'
STATUS = ROOT / 'supervisor-status.json'


def running(path):
    result = []
    for process in psutil.process_iter(['pid', 'cmdline']):
        try:
            if str(path) in (process.info['cmdline'] or []):
                result.append({'pid': process.pid, 'created_at': process.create_time()})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return result


def recoverable(state):
    reason = state.get('stop_reason')
    if reason in ('atividade_incomum', 'vagas_reservadas_por_envios_incertos', 'sessao_ou_conexao_indisponivel'):
        return True
    if reason == 'pre_checagem_falhou':
        detail = next((e.get('message', '') for e in reversed(state.get('events', [])) if e.get('kind') == 'pre_checagem_falhou'), '').lower()
        return 'atividade incomum' in detail or 'controle não encontrado' in detail
    return False


def reconcile(state, plan, inventory, now):
    """No submissions; uncertain clicks never become pending/retryable."""
    result = copy.deepcopy(state)
    limits = validate_plan(plan)
    changes = []
    complete = {cid: s for cid, s in state['scenes'].items() if s['status'] == 'complete'}
    recovered_pairs = set()
    for cid, scene in result['scenes'].items():
        if scene['status'] not in ('submitted', 'uncertain') or scene.get('video') or not scene['attempts']:
            continue
        attempt = scene['attempts'][-1]
        age = now - attempt['started_at']
        matches = [v for v in inventory['videos'] if v.get('created', [0])[0] >= attempt['started_at'] - 2
                   and norm(v.get('prompt') or '') == norm(attempt['prompt'])
                   and set(v.get('refs', [])) == {attempt['reference']['id']}]
        if len(matches) > 1:
            raise RuntimeError(cid + ': ambiguous provider receipts; manual review required.')
        if matches:
            video = matches[0]
            assert video.get('model') in ALLOWED_MODELS and video.get('seconds') == 8, 'Provider configuration mismatch.'
            scene.update(status='rendering', video=video['id'], model=video['model'], reserve=False,
                         render_started_at=attempt['started_at'], next_io_at=0)
            attempt['video'] = video['id']
            recovered_pairs.add(scene['pair'])
            changes.append({'cid': cid, 'action': 'recover_same_generation', 'video': video['id']})
        elif scene['status'] == 'submitted' and now - scene.get('submitted_at', attempt['started_at']) >= limits['confirmation_timeout']:
            scene.update(status='uncertain', reason='envio_sem_confirmacao', reserve=True,
                         detail='Preserved after cooldown; never retry a possible click.', finished_at=now)
            changes.append({'cid': cid, 'action': 'preserve_uncertain_click'})
        if not matches and age >= limits['rendering_timeout'] and scene.get('reserve'):
            scene.update(reserve=False, quarantined_at=now, retry_allowed=False,
                         quarantine_reason='pausa_30min_autorizada_prazo_render_excedido_sem_reenvio')
            changes.append({'cid': cid, 'action': 'release_expired_capacity_without_retry', 'age_seconds': age})
    for pair in recovered_pairs:
        for scene in result['scenes'].values():
            if scene['pair'] == pair and scene['status'] == 'blocked' and scene.get('reason') == 'dependencia_incompleta' and not scene['attempts']:
                scene.update(status='pending', next_io_at=0)
                scene.pop('reason', None)
                scene.pop('detail', None)
        if result['videos'][pair]['status'] != 'complete':
            result['videos'][pair].update(status='pending')
    assert all(result['scenes'][cid] == s for cid, s in complete.items())
    assert all(result['scenes'][cid]['status'] != 'pending' for cid, s in state['scenes'].items() if s['status'] == 'uncertain')
    return result, changes


def refresh():
    code = 'FLOW_RUN_DIR = ' + repr(str(ROOT)) + '\n' + (ROOT / 'refresh-retomada.py').read_text(encoding='utf-8')
    process = subprocess.run(['browser-harness'], input=code, text=True, capture_output=True,
                             cwd=BASE, timeout=150, **process_options())
    if process.returncode:
        raise RuntimeError(redact(process.stderr[-1400:]))
    return json.loads(next(line.removeprefix('REFRESH_RESULT=') for line in process.stdout.splitlines() if line.startswith('REFRESH_RESULT=')))


def prepare_resume():
    assert not running(CONTROLLER), 'Controller still running.'
    assert not macro_processes(BASE / 'scripts/flow_macro_windows.py'), 'Native macro still running.'
    assert not (ROOT / 'PARAR').exists(), 'Preserve explicit user stop.'
    handles = []
    try:
        for path in (BASE / '.flow_controller.lock', ROOT / '.noturno.lock'):
            handle = path.open('a')
            handles.append(handle)
            locks.flock(handle, locks.LOCK_EX | locks.LOCK_NB)
        observation = refresh()
        if observation['outcome'] != 'clear':
            return observation
        plan = read(ROOT / 'plano-noturno.json')
        original = read(ROOT / 'estado-noturno.json')
        inventory = Adapter(ROOT, plan, validate_plan(plan)).inventory()
        now = time.time()
        state, changes = reconcile(original, plan, inventory, now)
        receipt_path = ROOT / ('RETOMADA-30MIN-' + str(int(now)) + '.json')
        backup = ROOT / ('estado-antes-retomada-30min-' + str(int(now)) + '.json')
        atomic(backup, original)
        event = {'at': now, 'kind': 'retomada_automatica_30min', 'cid': None,
                 'message': 'Authorized cooldown completed; both project tabs refreshed and receipts reconciled; uncertain clicks never retried.'}
        state['events'].append(event)
        state.update(status='stopped', stop_reason='retomada_30min_preparada', updated_at=now)
        atomic(receipt_path, {'at': now, 'refresh': observation, 'backup': str(backup), 'changes': changes,
                              'generations_sent': 0, 'attempts_reset': False, 'completed_files_changed': False})
        atomic(ROOT / 'estado-noturno.json', state)
        with (ROOT / 'eventos-noturnos.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event) + '\n')
        hold = read(ROOT / 'BLOQUEIO-FLOW.json', {})
        if hold.get('status') == 'active':
            hold.update(status='resolved', resolved_at=now, resolution='authorized_30min_cooldown_refresh_clear',
                        new_submissions_allowed=True, uncertain_submissions_retried=False)
            atomic(ROOT / 'BLOQUEIO-FLOW.json', hold)
        marker = ROOT / 'PILOTOS-APROVADOS.json'
        if not marker.exists():
            backup_marker = ROOT / hold.get('pilot_marker_backup', '__missing__')
            assert backup_marker.parent == ROOT and backup_marker.is_file(), 'Pilot approval requires review.'
            backup_marker.replace(marker)
        return {'outcome': 'clear', 'receipt': str(receipt_path), 'changes': changes}
    finally:
        for handle in reversed(handles):
            handle.close()


def main():
    with (ROOT / '.supervisor-30min.lock').open('a') as lock:
        locks.flock(lock, locks.LOCK_EX | locks.LOCK_NB)
        status = read(STATUS, {})
        process = psutil.Process()
        status.update(pid=process.pid, created_at=process.create_time(), cooldown_seconds=DELAY,
                      user_instruction='quando travar: pausa 30 minutos, refresh nas abas e continua de onde parou')
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
        def save(**fields):
            status.update(at=time.time(), **fields)
            atomic(STATUS, status)
        def cool(reason):
            save(phase='cooldown', reason=reason, cooldown_started_at=time.time(), resume_after=time.time() + DELAY)
        try:
            while True:
                if (ROOT / 'PARAR').exists():
                    save(phase='user_stopped', reason='PARAR preserved')
                    return
                live = running(CONTROLLER)
                if live:
                    save(phase='running', controllers=live, resume_after=None)
                    time.sleep(10)
                    continue
                state = read(ROOT / 'estado-noturno.json')
                if all(v['status'] == 'complete' for v in state['videos'].values()):
                    audit = subprocess.run([sys.executable, str(ROOT / 'auditar-entrega.py')], cwd=BASE, capture_output=True, text=True, **process_options())
                    save(phase='complete_verified' if audit.returncode == 0 else 'audit_requires_review', audit=redact(audit.stdout or audit.stderr))
                    return
                if state.get('stop_reason') == 'parada_usuario':
                    save(phase='user_stopped', reason='parada_usuario preserved')
                    return
                if not recoverable(state) and status.get('phase') != 'cooldown':
                    save(phase='requires_review', reason=state.get('stop_reason') or state.get('status'))
                    return
                if status.get('phase') != 'cooldown':
                    cool(state.get('stop_reason'))
                if time.time() < status['resume_after']:
                    save(remaining_seconds=round(status['resume_after'] - time.time()))
                    time.sleep(min(10, max(1, status['resume_after'] - time.time())))
                    continue
                try:
                    save(phase='refreshing', remaining_seconds=0)
                    result = prepare_resume()
                    if result['outcome'] == 'manual':
                        save(phase='requires_review', reason='login_or_human_verification', result=result)
                        return
                    if result['outcome'] != 'clear':
                        cool('restriction_still_visible_after_refresh')
                        continue
                    save(phase='starting', result=result)
                    launch = subprocess.run([sys.executable, str(ROOT / 'iniciar-lote.py')], cwd=BASE,
                                            capture_output=True, text=True, timeout=30, **process_options())
                    if launch.returncode:
                        raise RuntimeError(launch.stderr or launch.stdout)
                    save(phase='running', launch=redact(launch.stdout), resume_after=None)
                    time.sleep(10)
                except Exception as error:
                    # No blind submission retry: another full cooldown precedes
                    # any refresh; source state and native journals remain intact.
                    detail = redact(error)
                    if any(word in detail.lower() for word in ('login', 'captcha', 'human verification', 'manual review', 'requires review', 'identity requires', 'configuration mismatch')):
                        save(phase='requires_review', reason=detail)
                        return
                    cool(detail)
        finally:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
