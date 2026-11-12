# Controlador acompanhado do lote de 20/10/2026

O lote PAR-066..120 está **concluído**, com 55 vídeos e 275 cenas.
Esta documentação descreve o controlador anterior `retomada-macro/lote-macro.py`.
Para uma nova leva, use [FLOW-NOTURNO.md](../../FLOW-NOTURNO.md).

O controlador antigo está vinculado aos IDs e à pasta de entrega daquele lote.
Seu código e registros foram preservados para auditoria e manutenção.

## Funcionamento

Cada vídeo tem cinco clipes de 8s. Hook e início da receita são independentes;
as cenas 3, 4 e 5 usam o último frame da receita anterior. Os lotes têm até dez
vídeos, com um macro nativo de envio na aba principal e consultas, uploads e
downloads pela aba auxiliar. As filas de I/O e montagem rodam separadamente.

Padrão: Elementos, Veo 3.1 Lite Lower Priority, 9:16, 8s, x1, 0 créditos;
até três renderizações, intervalo mínimo de 20s entre envios. A seleção da
referência e o texto integral são conferidos antes do clique único.

O estado vive em `PROGRESSO.json`, `spec.json.state.json`, `tarefas-macro.json`,
`referencias-novas.json`, `upload-lotes.json` e `eventos-macro.jsonl` dentro de
`retomada-macro/`. Downloads têm recibos com hashes; as montagens são conferidas
tecnicamente e não sobrescrevem entregas anteriores.

O fluxo acompanhado exige revisões visuais por ID em `qa/revisoes-cenas.json`,
com gates de etapas 4 e 5. `revisar.py` registra uma decisão humana ou da IA
após inspeção; ele não decide aprovação sozinho. Correções em cadeia e versões
rejeitadas ficam documentadas em `qa/`. Envios incertos nunca são repetidos
automaticamente.

O modo noturno atual usa um controlador próprio e identifica suas montagens
como pendentes de revisão visual. Não confunda os gates do lote antigo com os
relatórios de uma nova execução.

Resumo da entrega: [ESTADO-ATUAL.md](../../retomada-macro/ESTADO-ATUAL.md).
Os checkpoints detalhados e backups anteriores estão no
[histórico compactado](../../../_arquivo/2026-10-21/README.md).
