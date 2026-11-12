"""Resume falhas históricas locais, sem navegador e sem expor dados de sessão."""
import collections
import json
from pathlib import Path
import re
from noturno_core import atomic, redact

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'diagnostico-noturno'
CATEGORIES = [
    ('permissao', r'Acessibilidade.*(?:não|neg)|macOS não liberou', 'Pré-checagem antes da fila; parada global com relatório, sem tentar gerar.'),
    ('arquivo_ausente', r'FileNotFound|No such file|arquivo.*não.*encontr|Imagem inicial ausente|Arquivo.*ausente', 'Validar imagens por cena; recuperar downloads pelo mesmo ID; não bloquear outros vídeos.'),
    ('foco_ou_interface', r'controle sob o mouse mudou|controle mudou de posição|perdeu o foco|Controle não encontrado|Não achei o conteúdo|aba mudou|aba ativa precisa', 'Preparação com até três tentativas, somente antes de clicar; diário persistente do clique.'),
    ('upload', r'Seletor não respondeu|seletor de arquivo|upload.*(?:sem confirmação|pendente)|arquivo reenviado|upload.*timeout', 'Recibo antes da atribuição; após dúvida consultar o inventário sem reenviar arquivos.'),
    ('sessao_ou_consulta', r'IPCResponseTimeout|temporariamente indisponível|Erro de consulta|timed out|timeout|Aba principal ambígua', 'Prazos de I/O e reconexão das duas abas pelo projeto; limite global para indisponibilidade.'),
    ('envio_incerto', r'Macro não confirmou|Resolver tentativa registrada|Tentativa anterior precisa|Envio sem confirmação', 'Não repetir clique possivelmente enviado; isolar cena e reservar vaga de segurança.'),
    ('geracao_recusada', r'PUBLIC_ERROR_|Vídeo removido repetidamente|Geração recusada|Asset ausente confirmado', 'Registrar falha e seguir; nenhuma troca automática de pessoa ou conteúdo bloqueado.'),
    ('parada_usuario', r'Interrompido.*(?:Esc|canto superior)', 'Esc e canto continuam interrompendo a execução inteira; nunca contornar parada física.'),
]


def main():
    OUTPUT.mkdir(exist_ok=True)
    counts, examples = collections.Counter(), {}
    # Logs ativos e tentativas arquivadas: não contar cópias de backup do código.
    paths = list(ROOT.glob('*.log'))
    for folder in ('logs', 'erros-servidor', 'qa/rejeitados'):
        paths += list((ROOT / folder).rglob('*.log'))
    seen = set()
    for path in paths:
        for line in path.read_text(errors='replace').splitlines():
            for category, pattern, _ in CATEGORIES:
                if re.search(pattern, line, re.I):
                    # Mesmo erro de uma cena pode estar em log, traceback e arquivo.
                    normalized = re.sub(r'\d\d:\d\d:\d\d', '', redact(line)).strip()
                    signature = (category, normalized)
                    if signature not in seen:
                        counts[category] += 1
                        examples.setdefault(category, []).append(str(path.relative_to(ROOT)))
                        seen.add(signature)
                    break
    rejected = []
    for path in (ROOT / 'qa/rejeitados').glob('*/registro.json'):
        record = json.loads(path.read_text())
        rejected.append({'scene': path.parent.name, 'reason': redact(record.get('reason', '')), 'video': record.get('state', {}).get('video')})
    progress = json.loads((ROOT / 'PROGRESSO.json').read_text())
    data = {'historical_production': progress, 'diagnosis': [{'category': category, 'distinct_log_messages': counts[category],
             'examples': examples.get(category, [])[:4], 'correction': correction} for category, _, correction in CATEGORIES],
            'visual_rejections': rejected,
            'visual_limits': 'Sem modelo de visão, o modo noturno confere arquivos e conclui montagens para revisão; não aprova automaticamente mãos, objetos ou legendas.'}
    atomic(OUTPUT / 'ERROS-ANTERIORES.json', data)
    lines = ['# Diagnóstico da produção anterior', '',
             f"Entrega anterior: {progress['delivered_videos']}/{progress['planned_videos']} vídeos; {progress['done_scenes']} cenas concluídas.", '',
             'As contagens abaixo são mensagens distintas dos logs preservados, não uma contagem exata de gerações.', '',
             '| Categoria | Mensagens distintas | Correção |', '|---|---:|---|']
    lines += [f'| {category} | {counts[category]} | {correction} |' for category, _, correction in CATEGORIES]
    lines += ['', '## Defeitos visuais encontrados', '',
              'Os registros preservam duplicações de mãos, embalagens, utensílios e tampas, além de legendas indevidas. '
              'Esses defeitos pertencem à saída do gerador e não podem ser garantidos como ausentes por regras de arquivos. '
              'A fila noturna não depende da supervisão da IA: conclui as montagens tecnicamente válidas e as identifica como aguardando revisão visual.', '',
              '## O que mudou no controle da fila', '',
              'Erros de uma cena não encerram o lote. Falha de receita bloqueia apenas suas continuações; o hook é independente. '
              'Todo estado, tentativa, recibo e motivo ficam em disco. Upload, preparação, confirmação, geração e I/O têm limites. '
              'Não há repetição automática após um clique incerto. Três vagas incertas encerram com relatório em vez de enviar mais sem confirmação. '
              'Créditos fora do padrão, bloqueio da sessão e parada do usuário interrompem novos envios. '
              'Relatórios JSON e Markdown mostram arquivos montados, cenas faltantes, motivos e tentativas.', '',
              'Os 55 vídeos já entregues são preservados. Nenhuma geração nova foi necessária para estes testes.']
    (OUTPUT / 'ERROS-ANTERIORES.md').write_text('\n'.join(lines) + '\n')
    print('Diagnóstico:', OUTPUT / 'ERROS-ANTERIORES.md')


if __name__ == '__main__':
    main()
