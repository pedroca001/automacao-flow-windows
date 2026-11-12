# Execução noturna sem supervisão do Codex

**Windows:** use os atalhos de mesmo nome terminados em `.cmd` e carregue
`env.ps1` no PowerShell. Configuração do Chrome e instalação: [../WINDOWS.md](../WINDOWS.md).
Mantenha o PC ligado e desbloqueado. O restante da fila e dos relatórios é compartilhado.

1. Abra **Preparar Flow Noturno.command**. Informe a pasta das imagens e o link do projeto do Flow. O preparo apenas cria o plano; não envia imagens nem gera vídeos.
2. Abra **Flow Noturno.command**. A execução passa a rodar em segundo plano, independente do Codex e da janela do Terminal.
3. Na pasta da execução, consulte **RELATORIO-NOTURNO.md** ou **RELATORIO-NOTURNO.json**. Eles são atualizados durante a noite e ao terminar.

Use nomes como `PAR-001_hook.png` e `PAR-001_recipe.png`. Os nomes anteriores `134_novo_067_hook_copy22.png` e `133_novo_067_recipe_....png` também são reconhecidos. Cada par gera cinco cenas: hook e receita inicial independentes; depois continuações 3, 4 e 5 a partir dos frames finais. Os modelos de prompt padrão são os já usados nesta produção de receitas. Para outro conteúdo, forneça seu JSON de prompts em `--prompts` ao preparar.

Cada nova leva ganha pasta própria em `execucoes-noturnas/`. Os MP4s vão para `Montados para revisar` dentro dela. O plano contém a pasta de saída e permite configurar os prazos. Nenhum arquivo dos 55 vídeos anteriores é substituído. Preparar outra leva atualiza o atalho para o novo plano; não reutilize uma pasta de execução para um plano diferente.

Para receitas **sem hook**, use `preparar --somente-receita` e uma pasta com imagens
numeradas como `001_camping_05.png`. Esse modo usa apenas os quatro prompts da
receita (os antigos 2 a 5): a primeira cena parte da imagem inicial, e as outras
três partem do último frame anterior. São quatro cenas de 8s, concatenadas em um
MP4 de 32s, preservando o áudio ambiente gerado, sem locução adicional, legenda
ou efeitos. O nome final preserva o nome da imagem com sufixo `_32s.mp4`.

Planos de receita com `scheduling: "rolling_recipes"` usam uma janela contínua
de `limits.batch_size` receitas. Com tamanho 3, até três receitas avançam em
paralelo: cada continuação espera apenas seu próprio frame anterior, e uma
receita nova ocupa o lugar da que termina. O macro envia uma cena por vez; os
renders no Flow podem se sobrepor, respeitando `max_rendering: 3` e o intervalo
mínimo de 20 segundos. Um render antigo com ID é consultado novamente após
timeout: arquivo pronto é recuperado sem reenvio; ausência ou falha confirmada
pelo servidor libera sua vaga, mantendo o ID no histórico.

Mantenha o Mac ligado, com a tampa aberta e a sessão desbloqueada. O launcher evita repouso enquanto roda, mas não desativa bloqueio de tela, senha ou outros controles do macOS. O macro usa o mouse e teclado: não use o computador durante a produção. O Chrome deve estar logado no projeto e o Macro Flow precisa ter a autorização de Acessibilidade já concedida.

Para parar, abra **Parar Flow Noturno.command**, pressione Esc durante o macro ou coloque o ponteiro no canto superior esquerdo. A parada física continua valendo para a execução inteira. Depois de uma parada explícita, o arquivo `PARAR` permanece na pasta; remova-o conscientemente para continuar a mesma leva. Uma tentativa possivelmente clicada nunca é repetida automaticamente.

## Como os erros são tratados

- Imagem ausente, inválida ou ambígua: registrar a cena e seguir as outras. Uma referência inválida não reprova todos os arquivos do upload conjunto.
- Falha de preparação antes do clique: até três tentativas com atualização da aba. O diário do macro é sincronizado no disco antes do clique.
- Upload sem confirmação: consultar o recibo e inventário; não atribuir os arquivos novamente. Se continuar incerto, registrar e seguir.
- Erro de download ou arquivo corrompido: até três tentativas do mesmo vídeo, sem gerar outro. A transferência e o FFmpeg têm prazo.
- Render recusado, removido ou demorado: registrar o ID e a pendência; seguir o próximo vídeo. As continuações sem frame anterior ficam bloqueadas apenas naquela receita.
- Clique sem recibo: não repetir. Uma vaga fica reservada para evitar exceder três renderizações. Se todas as vagas ficarem incertas, encerrar com relatório das pendências.
- Falha de montagem: tentar novamente até o limite; preservar o arquivo existente e continuar montando os outros vídeos.
- Sem conexão, sessão bloqueada, créditos não confirmados em zero ou pedido de parada: encerrar novos envios com relatório. A automação não contorna login, CAPTCHA ou bloqueios do serviço.
- Crash inesperado do controlador: supervisor tenta retomar no máximo duas vezes, usando o estado e os recibos. Parada do usuário e conclusão com falhas não disparam esse reinício.

Limites padrão: lotes de até 10 vídeos, até 3 renderizações, 20 segundos entre envios, 3 minutos de preparação, 3 minutos para confirmação do envio, 40 minutos por render e 12 horas por execução. Os prazos ficam em `limits` no plano; as travas de até 3 renderizações e intervalo mínimo de 20 segundos são obrigatórias.

## Qualidade e relatório

O modo noturno verifica existência, duração, resolução, decodificação, hashes e último frame. Ele **não declara aprovação visual**. Mãos extras, objetos inventados e texto indevido são defeitos do modelo que não podem ser eliminados com garantia por essa checagem técnica. As montagens ficam prontas para revisão e aparecem no relatório como `visual_qa: not_reviewed`.

O relatório identifica vídeos completos e incompletos, cenas faltantes, falhas e bloqueios, IDs das gerações, quantidade de tentativas e pendências visuais. Os estados `uncertain` e `timed_out` preservam o recibo para investigar ou recuperar a geração existente, sem reenviá-la às cegas. Corrigir um arquivo de entrada após falha não reinicia a cena automaticamente na mesma noite; isso evita loops sem fim.

## Terminal

```bash
source ./env.sh
python3 retomada-macro/noturno.py preparar --imagens '/pasta/das/imagens' --projeto 'URL_OU_UUID'
python3 retomada-macro/noturno.py iniciar
python3 retomada-macro/noturno.py relatorio
python3 retomada-macro/noturno.py parar
```

Para um plano específico, acrescente `--plano '/pasta/plano-noturno.json'` a iniciar, executar, parar ou relatorio. `executar --validar` confere o plano e ferramentas locais sem abrir navegador, enviar imagens ou gerar vídeos. `executar` é a versão em primeiro plano; `iniciar` mantém o processo independente da conversa.

Testes sem gerações:

```bash
source ./env.sh
python3 -m unittest discover -s retomada-macro -p 'test_noturno*.py' -v
```

Validação de 20/10/2026: 28 testes passaram, incluindo I/O real com FFmpeg,
reparo de download, montagem de 40 segundos e exclusão mútua dos controladores.
As duas abas foram reencontradas no projeto, e o macro confirmou sua
configuração com recibo `prepared_without_click`. Nenhuma geração foi iniciada
nessa validação. Os hashes dos 55 vídeos entregues conferem com a auditoria
anterior. Evidências em `retomada-macro/testes-noturno.log` e
`retomada-macro/diagnostico-noturno/`.
