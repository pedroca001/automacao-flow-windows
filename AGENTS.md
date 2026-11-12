# Automação FLOW

No Windows, leia `WINDOWS.md`. Carregue `. .\env.ps1` (PowerShell) ou
`call env.cmd` (cmd) dentro de `sistema-criativos-e-vsl/`. Use os atalhos `.cmd`.
O macro Windows está em `scripts/flow_macro_windows.py`, sem compilação Swift.
O módulo `scripts/flow_platform.py` mantém travas e processos entre plataformas.
As instruções macOS abaixo continuam válidas apenas no Mac.

Mapa e estado atual: `README.md`. O lote PAR-066..120 de 20/10/2026 está
concluído (55 vídeos, 275 cenas). Não retome esse lote por instruções históricas.
Para novas levas de receitas, use `sistema-criativos-e-vsl/FLOW-NOTURNO.md`.
Para vídeos de personagens, use `sistema-criativos-e-vsl/FLOW-PERSONAGENS.md`.
São automações separadas: personagens usam `automacao-personagens/`, macro próprio,
`execucoes-personagens/` e `personagens-atual.json`. Não adaptar a fila de receitas
para personagens nem misturar os estados. Não operar as duas filas simultaneamente.
O resumo da produção está em `sistema-criativos-e-vsl/retomada-macro/ESTADO-ATUAL.md`.
Backups e checkpoints superados estão compactados em `_arquivo/`; consulte-os
somente para recuperação ou investigação histórica. A `.ignore` omite mídias e
históricos das buscas gerais; use o caminho explícito para inspecioná-los.

O sistema instalado está em `sistema-criativos-e-vsl/`, com a Atualização 08 aplicada.
Antes de operar o sistema, leia `sistema-criativos-e-vsl/SISTEMA.md` e o módulo da tarefa.
Trabalhe a partir dessa subpasta para resolver os caminhos relativos do fornecedor.

Carregue o ambiente com `source ./env.sh` antes de executar os scripts. Ele seleciona
o Python do projeto, o FFmpeg com libass, os modelos Whisper e o RVM já instalados.
Mapa dos scripts: `scripts/LEIA.md`. Estado da instalação: `INSTALACAO.md`.

As sete skills do fornecedor ficam em `sistema-criativos-e-vsl/SKILLS/`.
Quando o usuário solicitar uma delas, leia o `SKILL.md` correspondente:

- `criativos`: produção de anúncios.
- `vsl`: modelagem, geração e edição de VSL.
- `avatares-organicos`: persona e conteúdo orgânico.
- `direct-response-copywriter`: roteiro, CTA e oferta.
- `copy-legends`: headlines e estruturas de copy.
- `marketing-psychology`: persuasão.
- `video-ia-sem-defeito`: revisão mecânica de prompts de vídeo.

Para produção, use os scripts atualizados do fornecedor e seus gates de qualidade.
Gerações que consomem créditos e publicação dependem da solicitação do usuário.
Nunca registre tokens ou cookies em relatórios de instalação.
