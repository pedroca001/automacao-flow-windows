"""Entrada independente de preparação, cadastro e fila de personagens."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
from core import MODE, assign, atomic, choose_voices, project_id, read, sha, validate_plan
from client import browser

REGISTRY = HERE / '.state/registry.json'
POINTER = BASE / 'personagens-atual.json'


def locate(value):
    if value:
        return Path(value).resolve()
    pointer = read(POINTER, {})
    if not pointer.get('plan'):
        raise ValueError('Prepare primeiro uma leva de personagens.')
    return Path(pointer['plan'])


def config_file(path):
    data = read(path)
    if isinstance(data, list):
        return {'prompt_sets': {'teste': {'prompts': data}}}
    if set(data) == {str(i) for i in range(1, 6)}:
        return {'prompt_sets': {'teste': {'prompts': [data[str(i)] for i in range(1, 6)]}}}
    return data


def prepare(args):
    images = Path(args.imagens).resolve()
    files = sorted(p for p in images.iterdir() if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'))
    if not files:
        raise ValueError('Nenhum retrato encontrado.')
    root = Path(args.pasta).resolve() if args.pasta else BASE / 'execucoes-personagens' / datetime.now().strftime('%Y%m%d-%H%M%S')
    if (root / 'plano-personagens.json').exists():
        raise ValueError('Plano já existe. Retome-o ou prepare outra pasta.')
    metadata = read(args.metadata, {}) if args.metadata else {}
    catalog = read(args.vozes or HERE / 'voice_catalog.json')
    if not catalog:
        raise ValueError('Catálogo de vozes ausente. Descubra as vozes na interface antes de preparar.')
    registry = read(REGISTRY, {})
    existing = registry.get(args.projeto.rstrip('/'), {})
    characters, prior = [], {}
    for index, path in enumerate(files, 1):
        overrides = metadata.get(path.name, metadata.get(path.stem, {}))
        digest = sha(path)
        old = existing.get(digest, {})
        gender = overrides.get('gender', args.genero)
        if gender not in ('female', 'male'):
            raise ValueError('Informe gênero em --genero ou no metadata para ' + path.name)
        cid = path.stem
        name = old.get('name') or overrides.get('name') or datetime.now().strftime('AV%Y%m%d_') + f'{index:02d}_' + path.stem
        characters.append({'id': cid, 'name': name, 'image': str(path), 'image_sha256': digest, 'gender': gender, 'tags': overrides.get('tags', [])})
        if old:
            prior[cid] = old['voice']
    prior.update({'registry_' + key: value['voice'] for key, value in existing.items()})
    voices = choose_voices(characters, catalog, prior=prior)
    for character in characters:
        character['voice'] = voices[character['id']]
        character['voice_label'] = next(v['label'] for v in catalog if v['name'] == character['voice'])
    config = config_file(args.prompts) if args.prompts else {}
    plan = {'mode': MODE, 'schema': 1, 'project_url': args.projeto.rstrip('/'), 'project': project_id(args.projeto),
            'output': str(Path(args.saida).resolve()), 'characters': characters, 'prompt_sets': config.get('prompt_sets', {}),
            'assignments': assign(characters, config), 'limits': {}}
    validate_plan(plan)
    atomic(root / 'plano-personagens.json', plan)
    for character in characters:
        old = existing.get(character['image_sha256'])
        if old:
            atomic(root / 'characters' / (character['id'] + '.json'), old)
    atomic(POINTER, {'plan': str(root / 'plano-personagens.json')})
    print(f'Plano de personagens preparado: {len(characters)} avatares; {len(characters)*5 if plan["prompt_sets"] else 0} cenas com prompts definidos.')
    print(root / 'plano-personagens.json')
    print('Nenhuma geração executada.')


def set_prompts(path, source):
    plan = read(path)
    if (path.parent / 'estado-personagens.json').exists():
        raise ValueError('A fila já foi materializada. Crie outra leva para alterar prompts ou atribuições.')
    config = config_file(source)
    plan['prompt_sets'] = config['prompt_sets']
    plan['assignments'] = assign(plan['characters'], config)
    validate_plan(plan, require_prompts=True)
    atomic(path, plan)
    print('Cinco prompts por personagem definidos; atribuições fixadas no plano.')


def register(path):
    plan = read(path)
    validate_plan(plan)
    registry = read(REGISTRY, {})
    for character in plan['characters']:
        record = browser(plan, path.parent, 'register', character=character)
        registry.setdefault(plan['project_url'], {})[character['image_sha256']] = record
        atomic(REGISTRY, registry)
        print(character['id'] + ': ' + record['phase'] + ' / voz ' + character['voice'], flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('preparar')
    p.add_argument('--imagens', required=True)
    p.add_argument('--saida', required=True)
    p.add_argument('--projeto', required=True)
    p.add_argument('--genero', choices=('female', 'male'))
    p.add_argument('--metadata')
    p.add_argument('--vozes')
    p.add_argument('--prompts')
    p.add_argument('--pasta')
    for action in ('definir-prompts', 'cadastrar', 'validar', 'executar', 'iniciar', 'parar', 'relatorio', 'reconciliar-falha', 'substituir-cena', 'revisar-cena', 'reprovar-qualidade', 'sinalizar-qualidade'):
        p = commands.add_parser(action)
        p.add_argument('--plano')
        if action == 'definir-prompts':
            p.add_argument('--arquivo', required=True)
        if action == 'substituir-cena':
            p.add_argument('--conjunto',required=True)
            p.add_argument('--cena',required=True,type=int,choices=range(1,6))
            p.add_argument('--arquivo',required=True)
        if action == 'revisar-cena':
            p.add_argument('--cena',required=True)
            p.add_argument('--arquivo',required=True)
            p.add_argument('--compartilhar-bloqueadas',action='store_true')
        if action in ('reprovar-qualidade','sinalizar-qualidade'):
            p.add_argument('--cena',required=True)
            p.add_argument('--motivo',required=True)
    args = parser.parse_args()
    if args.action == 'preparar':
        return prepare(args)
    path = locate(args.plano)
    if args.action == 'definir-prompts':
        return set_prompts(path, args.arquivo)
    if args.action == 'validar':
        plan = read(path)
        validate_plan(plan, require_prompts=True)
        for character in plan['characters']:
            if sha(character['image']) != character['image_sha256']:
                raise ValueError('Imagem alterada: ' + character['id'])
        print('Plano local válido. Nenhum navegador, upload ou geração executado.')
        return 0
    from controller import run, start, stop, report, controller_lock, reconcile_failure, replace_scene, submit_review, reject_quality, submit_quality
    if args.action=='sinalizar-qualidade':
        return submit_quality(path,args.cena,args.motivo)
    if args.action=='reprovar-qualidade':
        return reject_quality(path,args.cena,args.motivo)
    if args.action=='revisar-cena':
        return submit_review(path,args.cena,args.arquivo,args.compartilhar_bloqueadas)
    if args.action=='reconciliar-falha':
        return reconcile_failure(path)
    if args.action=='substituir-cena':
        return replace_scene(path,args.conjunto,args.cena,args.arquivo)
    if args.action == 'cadastrar':
        with controller_lock(path.parent):
            return register(path)
    return {'executar':run, 'iniciar':start, 'parar':stop, 'relatorio':report}[args.action](path)


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except Exception as error:
        import os
        if os.environ.get('FLOW_CHARACTER_DEBUG')=='1':
            import traceback
            traceback.print_exc()
        print('ERRO:', str(error), file=sys.stderr)
        sys.exit(2)
