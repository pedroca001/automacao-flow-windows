# Macro do Flow com mouse e teclado nativos

Para novas levas de receitas, use [FLOW-NOTURNO.md](FLOW-NOTURNO.md).
Para uma cena individual, abra **Macro Flow.app** nesta pasta ou use o terminal.
Todos os comandos abaixo partem de `sistema-criativos-e-vsl/`.

O aplicativo instalado fica em `~/Library/Application Support/Flow Macro/`;
o atalho desta pasta aponta para ele. Deixe o projeto correto aberto no Chrome.
O macro usa o mouse e teclado do Mac; aguarde sem interagir durante a operação.

## Configuração e preparação

```bash
source ./env.sh
./flow-macro --configurar
./flow-macro --arquivo /caminho/prompt.txt --elemento NOME.png --preparar
```

`--configurar` apenas seleciona e confere opções. `--preparar` também preenche
e confere o prompt, sem clicar em gerar. `--inspecionar` lê os controles.
`--elemento` seleciona pelo nome exato uma referência já enviada ao projeto;
sem ele, a referência precisa estar previamente selecionada.

## Envio de uma cena solicitada

```bash
./flow-macro --arquivo /caminho/prompt.txt --elemento NOME.png --projeto ID_DO_PROJETO
```

O padrão atual é **Elementos, Veo 3.1 Lite Lower Priority, 9:16, 8s, x1**,
com conferência de **0 créditos** antes do clique. O prompt é digitado por
press/release (`--keystrokes`) e conferido por inteiro. `--copiar` é uma opção
explícita. `--substituir` permite substituir um prompt diferente já preenchido.

Há um único clique de geração. A limpeza do campo confirma apenas a reação
da interface; o controlador acompanha o vídeo separadamente. Um envio incerto
exige conferir o resultado existente antes de qualquer repetição.

Esc, Ctrl+C ou o ponteiro no canto superior esquerdo interrompem o macro.
O aplicativo e os scripts compartilham `FLOW_LOCK`, definido pelo ambiente e,
no aplicativo, pelo `FlowSystemDirectory` do `Info.plist`.

## Instalação e manutenção

O fonte é `scripts/flow_macro.swift`; o binário local está em `.local-bin/`.
`./flow-macro --compilar` recompila se necessário, atualiza o aplicativo e
confere sua assinatura. O cache Swift é recriado quando necessário.

A Acessibilidade deve estar autorizada para **Macro Flow** nos Ajustes do
macOS. `./flow-macro --pedir-permissao` solicita a autorização. Uma mudança
do aplicativo pode exigir renovar essa permissão. O funcionamento depende dos
controles em português na interface do Flow.

Na validação de 20/10, o preparo real passou sem geração. O macro também foi
usado no lote concluído de 55 vídeos. As evidências estão em
`retomada-macro/diagnostico-noturno/`; o resumo está em
[ESTADO-ATUAL.md](retomada-macro/ESTADO-ATUAL.md).

Ferramentas auxiliares: [integração individual](docs/automacao/FLOW-INTEGRADO.md)
e [controlador acompanhado anterior](docs/automacao/FLOW-DUAS-ABAS.md).
O driver do fornecedor continua em `scripts/flow_driver.py`.
