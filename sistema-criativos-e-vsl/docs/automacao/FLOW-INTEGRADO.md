# Integração individual do macro com acompanhamento

Ferramenta auxiliar `flow-integrado`, preservada para envio e acompanhamento
de uma cena. Para novas levas de receitas, use o
[modo noturno](../../FLOW-NOTURNO.md). Os comandos abaixo partem de
`sistema-criativos-e-vsl/`, com `source ./env.sh`.

O macro envia pelo botão; a integração observa a resposta e acompanha os IDs
retornados. Não substitui tokens de reCAPTCHA. O driver e o downloader do
fornecedor permanecem disponíveis separadamente.

Com o projeto ativo no Chrome e a referência já selecionada:

```bash
./flow-integrado verificar --projeto ID_DO_PROJETO
./flow-integrado enviar --arquivo /caminho/prompt.txt --projeto ID_DO_PROJETO --id CENA-001 --saida /caminho/clipes --aguardar 600 --keystrokes
```

O macro mantém Elementos, Lite Lower Priority, 9:16, 8s, x1 e verificação de
0 créditos. O padrão atual do macro é digitação por teclas. Use `--keystrokes`
explicitamente nesta integração para manter também seu registro de transporte
coerente. `--substituir` autoriza substituir um prompt preenchido.

Cada ID tem estado e cópia do prompt. Uma tentativa registrada não é reenviada
automaticamente. Para retomar somente consulta e download:

```bash
./flow-integrado acompanhar --estado /caminho/clipes/CENA-001.estado.json --aguardar 600
```

As consultas têm intervalo de 20s; o download usa a URL assinada do vídeo.
Existência, duração, resolução e decodificação são conferidas. A revisão visual
continua necessária. Envio incerto, recusa ou identificação ambígua interrompem
o fluxo para investigação; não repita uma geração sem conferir o ID existente.

O código está em `scripts/flow_integrado.py`. A ferramenta usa travas e o
aplicativo instalado; não execute outro controlador ao mesmo tempo.
Os detalhes dos testes e ajustes anteriores estão no
[histórico compactado](../../../_arquivo/2026-10-21/README.md).
