# Instalação local

**Windows:** siga [../WINDOWS.md](../WINDOWS.md). O ambiente Windows usa
`env.ps1` / `env.cmd`, `requirements-windows.txt` e os atalhos `.cmd`.
As evidências e caminhos do Mac registrados abaixo são históricos.

Pacote do fornecedor com a Atualização 08 aplicada. O driver e o downloader
originais foram preservados. As extensões locais acrescentam o macro nativo
do macOS e a fila noturna de receitas.

Execute a partir desta pasta com `source ./env.sh`, ou use `./criativos-run`.
O ambiente mantém Python em `.venv/`, FFmpeg com libass, Whisper e RVM.
As sete skills têm fonte em `SKILLS/` e cópias instaladas em `.claude/skills/`.

## Entradas de operação

- [FLOW-NOTURNO.md](FLOW-NOTURNO.md): preparar, iniciar, acompanhar e parar novas levas de receitas.
- [MACRO-FLOW.md](MACRO-FLOW.md): aplicativo e comandos para uma cena.
- [Scripts do fornecedor](scripts/LEIA.md).
- [Integração individual](docs/automacao/FLOW-INTEGRADO.md) e [controlador acompanhado anterior](docs/automacao/FLOW-DUAS-ABAS.md).

`Macro Flow.app` aponta para o aplicativo instalado em
`~/Library/Application Support/Flow Macro/Macro Flow.app`. O binário local
fica em `.local-bin/`. O macro e os controladores compartilham travas para
impedir envios simultâneos. A autorização de Acessibilidade pertence ao aplicativo;
uma recompilação pode exigir renová-la no macOS.

## Validação registrada

Em 20/10/2026 passaram 28 testes do modo noturno, incluindo I/O com FFmpeg,
reparo de download, montagem de 40s e exclusão mútua dos controladores.
O preparo real encontrou as duas abas e confirmou `prepared_without_click`.
Evidências: `retomada-macro/testes-noturno.log` e
`retomada-macro/diagnostico-noturno/`. O funcionamento online depende da
interface atual do Flow e da sessão do Chrome.

O lote anterior está concluído: 55 vídeos e 275 cenas. Consulte
[ESTADO-ATUAL.md](retomada-macro/ESTADO-ATUAL.md).

Na organização de 21/10, backups e instruções superadas foram compactados em
`../_arquivo/2026-10-21/`; caches regeneráveis foram removidos. Ambiente,
código de produção, clipes, frames, recibos e entregas foram preservados.

Na conferência após a limpeza de 21/10, o pacote permaneceu completo e os
28 testes passaram novamente. Os hashes dos 55 vídeos finais conferem; não
houve geração ou teste online nessa limpeza.

Conferência local, sem gerações:

```bash
source ./env.sh
bash scripts/verificar-pacote.sh
python3 -m unittest discover -s retomada-macro -p 'test_noturno*.py' -v
```
