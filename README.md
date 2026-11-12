# Automação Google Flow — Windows

Automação local de geração de vídeos no Google Flow com macro nativo do Windows,
fila persistente, recibos por tentativa, download, composição por FFmpeg e auditoria.

- **[Instalação e uso no Windows](WINDOWS.md)**: instalador, atalhos `.cmd`, Chrome e ambiente.
- **[Receitas com pausa e retomada automática](sistema-criativos-e-vsl/modelos/lote-receitas-windows/README.md)**:
  modelo de 1.200 receitas padrão/azeite e supervisor de 30 minutos com refresh.
- **[Fila noturna](sistema-criativos-e-vsl/FLOW-NOTURNO.md)**: preparação e operação geral.
- **[Personagens](sistema-criativos-e-vsl/FLOW-PERSONAGENS.md)**: automação separada das receitas.

## Começar

Instale Python/uv, FFmpeg com libass e Chrome conforme `WINDOWS.md`.
Execute `Instalar Windows.cmd`, depois `Preparar Flow Noturno.cmd` e `Flow Noturno.cmd`.
Para a leva de receitas com sincronização e supervisor, siga o modelo acima.

O macro confere Vídeo / Elementos / Veo 3.1 Lite Lower Priority / 9:16 / 8s /
x1 / zero créditos antes de enviar. O navegador precisa estar autenticado e o
computador ligado/desbloqueado, com mouse e teclado livres durante a operação.
Uma tentativa possivelmente enviada é preservada e reconciliada antes de qualquer retomada.

O repositório contém código, scripts, prompts, testes e documentação. Não contém
tokens, cookies, sessões do navegador, imagens, vídeos, modelos instalados,
ambientes Python, backups ou históricos das execuções. As configurações reais
permanecem locais; use os arquivos `.example` como referência.

## Origem

Versão Windows derivada de `pedroca001/automacao-flow-mac`, com as adaptações locais
e o supervisor de pausa/refresh/retomada. Os módulos e documentos originais do
fornecedor foram preservados. Instruções Swift, `.command` e `env.sh` são do macOS;
no Windows use os atalhos `.cmd` e `env.ps1`/`env.cmd`.
