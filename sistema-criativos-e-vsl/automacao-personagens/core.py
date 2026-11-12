"""Planos e recibos exclusivos da automação de personagens."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time
from urllib.parse import urlparse

MODE = 'flow_characters_v1'
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}')


def read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else copy.deepcopy(default)


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.{time.time_ns()}.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def project_id(url):
    parsed = urlparse(url)
    match = re.fullmatch(r'/(?:u/\d+/)?project/([a-f0-9-]{36})/?', parsed.path)
    if parsed.scheme != 'https' or parsed.hostname != 'flow.google.com' or not match or parsed.query or parsed.fragment:
        raise ValueError('Informe a URL exata do projeto no Flow, incluindo /u/N.')
    return match[1]


def validate_prompts(prompts):
    if not isinstance(prompts, list) or len(prompts) != 5:
        raise ValueError('Cada conjunto precisa ter exatamente cinco prompts.')
    for item in prompts:
        text = item if isinstance(item, str) else item.get('text', '') if isinstance(item, dict) else ''
        if not text.strip() or re.search(r'\{[A-Z_]+\}|PREENCHER|PROMPT_[1-5]', text):
            raise ValueError('Há prompt vazio ou placeholder.')
        if any((ord(c) < 32 and c not in '\n\r') or ord(c) == 127 for c in text):
            raise ValueError('Prompt contém caracteres de controle.')
    return prompts


def prompt_text(item):
    return item if isinstance(item, str) else item['text']


def extract_spoken(text):
    match=re.search(r'(?is)(?:Spoken audio only, not on-screen text:|Spoken audio only:|Exact spoken dialogue:|Exact dialogue:)\s*["“](.*?)["”]\s*$',text)
    return match[1] if match else None


def validate_revision(scene, text):
    expected=scene.get('spoken') or extract_spoken(scene['prompt'])
    if not expected or extract_spoken(text)!=expected:
        raise ValueError('A frase falada precisa permanecer exatamente igual, incluindo pontuação.')
    retry_service_error=(scene.get('reason')=='falha_recuperavel_do_servico_confirmada_na_interface'
        and 'atividade incomum' in scene.get('failure_evidence',{}).get('message','').lower())
    if text.strip()==scene['prompt'].strip() and not retry_service_error:
        raise ValueError('A revisão precisa esclarecer as instruções; não repetir o mesmo prompt recusado.')
    return expected


def assign(characters, config):
    """Resolve uma vez; a fila lê a atribuição gravada, nunca sorteia na retomada."""
    sets = config.get('prompt_sets', {})
    if not sets:
        return {}
    for key, value in sets.items():
        if not ID.fullmatch(key):
            raise ValueError('ID de conjunto inválido: ' + key)
        validate_prompts(value['prompts'])
    distribution = config.get('distribution', {'mode': 'cycle'})
    rng = random.Random(distribution.get('seed', 0))
    explicit = config.get('assignments', {})
    unknown = set(explicit) - {c['id'] for c in characters}
    if unknown:
        raise ValueError('Personagem desconhecido nas atribuições: ' + ', '.join(sorted(unknown)))
    quotas = dict(distribution.get('quotas', {}))
    if distribution.get('mode') == 'quota' and (set(quotas) != set(sets) or any(type(n) is not int or n < 0 for n in quotas.values()) or sum(quotas.values()) != len(characters)):
        raise ValueError('As cotas devem totalizar o número de personagens e nomear todos os conjuntos.')
    if distribution.get('mode')=='quota':
        compatible={c['id']:[key for key,value in sets.items() if c['gender'] in value.get('genders',['female','male']) and set(value.get('required_tags',[])).issubset(c.get('tags',[])) and (c['id'] not in explicit or explicit[c['id']]==key)] for c in characters}
        slots=[key for key,amount in quotas.items() for _ in range(amount)]
        occupied={}
        def place(cid,visited):
            for index,key in enumerate(slots):
                if index in visited or key not in compatible[cid]:
                    continue
                visited.add(index)
                if index not in occupied or place(occupied[index],visited):
                    occupied[index]=cid
                    return True
            return False
        for c in sorted(characters,key=lambda c:len(compatible[c['id']])):
            if not place(c['id'],set()):
                raise ValueError('Não há distribuição que atenda às cotas, gêneros e tags.')
        inverse={cid:slots[index] for index,cid in occupied.items()}
        return {c['id']:inverse[c['id']] for c in characters}
    result = {}
    for index, character in enumerate(characters):
        eligible = [key for key, value in sets.items()
                    if character['gender'] in value.get('genders', ['female', 'male'])
                    and set(value.get('required_tags', [])).issubset(character.get('tags', []))]
        if distribution.get('mode') == 'quota':
            eligible = [key for key in eligible if quotas.get(key, 0) > 0]
        if not eligible:
            raise ValueError('Nenhum conjunto compatível com ' + character['id'])
        selected = explicit.get(character['id'])
        if selected is not None and selected not in eligible:
            raise ValueError('Atribuição incompatível com gênero/tags/cota: ' + character['id'])
        mode = distribution.get('mode', 'cycle')
        if mode not in ('cycle', 'random', 'quota'):
            raise ValueError('Distribuição deve ser cycle, random ou quota.')
        if selected is None:
            selected = rng.choice(eligible) if mode == 'random' else eligible[index % len(eligible)] if mode == 'cycle' else eligible[0]
        result[character['id']] = selected
        if mode == 'quota':
            quotas[selected] -= 1
    return result


def choose_voices(characters, catalog, prior=None, seed=None):
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    prior = prior or {}
    assigned, used = {}, set(prior.values())
    for character in characters:
        if character['id'] in prior:
            name = prior[character['id']]
            if not any(v['name'] == name and v['gender'] == character['gender'] for v in catalog):
                raise ValueError('Voz previamente atribuída incompatível com ' + character['id'])
        else:
            eligible = [v['name'] for v in catalog if v['gender'] == character['gender']]
            if not eligible:
                raise ValueError('Não há vozes do gênero ' + character['gender'])
            name = rng.choice([v for v in eligible if v not in used] or eligible)
        assigned[character['id']] = name
        used.add(name)
    return assigned


def validate_plan(plan, require_prompts=False):
    if plan.get('mode') != MODE or project_id(plan['project_url']) != plan.get('project'):
        raise ValueError('Plano não pertence à automação de personagens ou projeto diverge.')
    chars = plan.get('characters', [])
    ids = [c['id'] for c in chars]
    if not chars or len(set(ids)) != len(ids) or any(not ID.fullmatch(k) for k in ids):
        raise ValueError('IDs de personagem inválidos ou duplicados.')
    names = [c['name'] for c in chars]
    if len(set(names)) != len(names):
        raise ValueError('Nomes de personagem precisam ser únicos no plano.')
    for char in chars:
        if char['gender'] not in ('female', 'male') or not char.get('voice') or not char.get('image_sha256'):
            raise ValueError('Gênero, voz ou hash ausente: ' + char['id'])
    sets = plan.get('prompt_sets', {})
    mapping = plan.get('assignments', {})
    if require_prompts and (not sets or set(mapping) != set(ids)):
        raise ValueError('Faltam os cinco prompts e as atribuições; cadastro pode continuar sem gerar.')
    for value in sets.values():
        validate_prompts(value['prompts'])
    for cid, key in mapping.items():
        if cid not in ids or key not in sets:
            raise ValueError('Atribuição aponta para personagem/conjunto inexistente.')
        char = next(c for c in chars if c['id'] == cid)
        if char['gender'] not in sets[key].get('genders', ['female', 'male']) or not set(sets[key].get('required_tags', [])).issubset(char.get('tags', [])):
            raise ValueError('Atribuição de conjunto incompatível com ' + cid)
    limits = {'max_rendering': 3, 'send_interval': 1, 'native_timeout': 240, 'confirmation_timeout': 180,
              'render_timeout': 2400, 'poll_interval': 2, 'max_run_seconds': 43200, 'generation_attempts':3, **plan.get('limits', {})}
    if (limits['max_rendering'] is not None and (type(limits['max_rendering']) is not int or limits['max_rendering']<1)) or limits['send_interval'] < 1:
        raise ValueError('Vagas devem ser um inteiro positivo ou null, e intervalo minimo de um segundo.')
    if any(not isinstance(v, (int, float)) or v <= 0 for key,v in limits.items() if key!='max_rendering'):
        raise ValueError('Prazos devem ser positivos.')
    if type(limits['generation_attempts']) is not int or not 1<=limits['generation_attempts']<=3:
        raise ValueError('Máximo de três tentativas de geração por cena.')
    return limits


def operating_limits(limits,settings):
    result={**limits}
    if 'max_rendering' in settings:
        count=settings['max_rendering']
        if count is not None and (type(count) is not int or count<1):
            raise ValueError('Vagas devem ser um inteiro positivo ou null para sem teto local.')
        result['max_rendering']=count
    return result


def build_scenes(plan):
    validate_plan(plan, require_prompts=True)
    result = {}
    for character in plan['characters']:
        key = plan['assignments'][character['id']]
        for number, item in enumerate(plan['prompt_sets'][key]['prompts'], 1):
            cid = character['id'] + '__' + key + f'__{number:02d}'
            result[cid] = {'character': character['id'], 'prompt_set': key, 'number': number,
                           'prompt': prompt_text(item), 'spoken': (item.get('spoken') or extract_spoken(item['text'])) if isinstance(item, dict) else extract_spoken(item),
                           'prompt_sha256': fingerprint(prompt_text(item)), 'status': 'pending', 'attempts': []}
    return result


def output_filename(character,group):
    filename=character['name']+'__'+group+'__40s.mp4'
    if re.search(r'[<>:"/\\|?*\x00-\x1f]',filename):
        raise ValueError('Nome do personagem não pode formar um arquivo Windows seguro.')
    return filename


def page_block_reason(full_text, outside_error_tiles, retry_error_tiles=False):
    """Distingue desafio global de um cartao de geracao com falha recuperavel."""
    text=full_text.lower()
    if any(term in text for term in ('verifique se você é humano','verify you are human')):
        return 'verificacao_humana'
    unusual=('unusual activity','atividade incomum')
    if any(term in outside_error_tiles.lower() for term in unusual):
        return 'atividade_incomum_global'
    if any(term in text for term in unusual) and not retry_error_tiles:
        return 'atividade_incomum_cartao_sem_autorizacao'
    return None


def reserved_generation_slots(scenes,reservations,now):
    keys=set()
    for cid,scene in scenes.items():
        if scene['status']!='uncertain':continue
        release=scene.get('reservation_release',{})
        expired_and_checked=(release.get('attempt')==len(scene['attempts'])
            and 0<release.get('expires_at',0)<=release.get('absence_confirmed_at',0)<=now)
        if not expired_and_checked:keys.add((cid,len(scene['attempts'])))
    keys.update((r['scene'],r['attempt']) for r in reservations.values() if r['expires_at']>now)
    return len(keys)


def missing_asset_failure(scene,result,inventory,now):
    """Confirma desaparecimento do ID antes de classificar RPC 5 como falha."""
    if result.get('rpc_code')==5 and scene.get('video') not in inventory['asset_ids']:
        started=scene.setdefault('missing_asset_since',now)
        return now-started>=10
    scene.pop('missing_asset_since',None)
    return False


def reconcile(scene, inventory, receipt, now, confirmation_timeout):
    """Envio possivelmente clicado nunca volta a pending por conta própria."""
    attempt = scene['attempts'][-1]
    baseline = set(attempt['baseline'])
    matches = [v for v in inventory['videos'] if v['id'] not in baseline and v.get('prompt', '').strip() == scene['prompt'].strip()]
    if scene.get('expected_character_id'):
        matches=[v for v in matches if scene['expected_character_id'] in v.get('refs',[])]
    if len(matches) == 1:
        video = matches[0]
        if video.get('model') != 'veo_3_1_r2v_lite_low_priority':
            scene.update(status='failed', reason='modelo_divergente', video=video['id'])
        else:
            scene.pop('reason',None)
            scene.update(status='rendering', video=video['id'], sent_at=attempt['started_at'],server_model=video.get('model'),server_refs=video.get('refs',[]))
    elif len(matches) > 1:
        scene.update(status='uncertain', reason='identificacao_ambigua')
    elif receipt.get('phase') in ('click_intent', 'submitted_ui'):
        scene['status'] = 'confirming'
        if now - attempt['started_at'] > confirmation_timeout:
            scene.update(status='uncertain', reason='clique_sem_id')
    else:
        scene.update(status='failed', reason='preparacao_sem_clique')
    return scene
