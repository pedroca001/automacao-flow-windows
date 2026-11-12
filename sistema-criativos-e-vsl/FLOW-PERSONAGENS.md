# Automação de personagens — processo separado das receitas

Existem duas automações independentes neste projeto:

| | Receitas | Personagens |
|---|---|---|
| Documentação | `FLOW-NOTURNO.md` | este arquivo |
| Controlador | `retomada-macro/noturno.py` | `automacao-personagens/cli.py` e `controller.py` |
| Macro de geração | `scripts/flow_macro_windows.py` | `automacao-personagens/macro_personagens.py` |
| Imagens | pares hook/recipe | um retrato por personagem |
| Continuidade | receita e frames finais encadeados | cinco cenas independentes usando o personagem cadastrado |
| Prompts | modelos de receita | conjuntos de cinco prompts, atribuídos por personagem |
| Estado | `execucoes-noturnas/`, `noturno-atual.json` | `execucoes-personagens/`, `personagens-atual.json` |
| Entrega | pasta do plano de receitas | pasta `--saida` do plano de personagens |

O código e os estados da receita não são alterados pelo novo processo. As duas
automações usam a mesma trava de exclusão do navegador: não devem controlar mouse,
teclado e projeto simultaneamente. O novo macro reaproveita as rotinas de
acessibilidade e configuração do macro Windows, mas possui entrada própria,
seleção exclusiva de recurso **Personagem** e verificação do projeto com `/u/N`.
O download reaproveita apenas a leitura validada de arquivos do fornecedor.

## Fluxo

1. Conferir os retratos e registrar gênero e, se necessário, categorias em `tags`.
2. Preparar um plano exclusivo. Atribuições de voz e de conjunto de prompts são
   sorteadas/resolvidas uma vez e ficam gravadas; retomar não sorteia novamente.
3. Pelo navegador: **Personagens → Novo personagem → Enviar**. Enviar somente o
   retrato, selecionar uma voz do gênero registrado, dar nome e concluir.
   Informações sobre o personagem ficam vazias; não gerar corpo nem retrato novo.
4. Pelo **macro nativo de personagens**: selecionar o personagem já cadastrado,
   preencher o prompt e gerar uma cena. O navegador não clica em gerar nem envia
   requisições de geração. Configuração: **Vídeo / Elementos / 9:16 / Veo 3.1 Lite
   Lower Priority / 8s / x1 / 0 créditos**.
5. Consultar IDs e andamento, baixar os cinco clipes e montar em ordem, sem
   transições ou cortes que reduzam os 40 segundos.
6. Entregar o MP4 de cada personagem na pasta configurada, acompanhado do tracking
   na pasta da execução. As montagens aguardam revisão visual e de voz.

Vozes são sorteadas entre as do gênero correto, evitando repetição enquanto há
opções livres. Quando acabam, podem repetir. A seleção vem do catálogo observado
na interface; uma voz indisponível interrompe o cadastro em vez de escolher outra
silenciosamente. Personagens já cadastrados no mesmo projeto e com o mesmo hash
de retrato podem ser reutilizados com nome e voz preservados pelo registro local.
O registro fica em `automacao-personagens/.state/registry.json`.

## Windows

Abra o projeto correto no Chrome normal, com depuração remota permitida e
acessibilidade habilitada, conforme `../WINDOWS.md`. Mantenha o computador
desbloqueado e não use mouse/teclado enquanto o macro opera.

No PowerShell, dentro de `sistema-criativos-e-vsl/`:

```powershell
. .\env.ps1
python automacao-personagens\cli.py preparar --imagens 'S:\pasta\Avatares' --saida 'S:\pasta\Videos Prontos' --projeto 'https://flow.google.com/u/1/project/UUID' --genero female --prompts 'prompts.json'
python automacao-personagens\cli.py validar
python automacao-personagens\cli.py cadastrar
python automacao-personagens\cli.py iniciar
python automacao-personagens\cli.py relatorio
python automacao-personagens\cli.py parar
```

O comando `preparar` não abre navegador nem gera. Pode preparar sem `--prompts`
para cadastrar os personagens antes de receber o texto. Depois use
`definir-prompts --arquivo prompts.json`; a alteração só é permitida antes de a
fila de cenas ser materializada. `validar` exige cinco prompts válidos e verifica
os hashes das imagens sem operar o navegador. `cadastrar` envia retratos e salva
personagens, mas não gera vídeos.

`executar` acompanha em primeiro plano; `iniciar` cria um processo independente
da janela e do Codex. Os atalhos **Personagens Flow.cmd**, **Relatorio Personagens
Flow.cmd** e **Parar Personagens Flow.cmd** usam exclusivamente essa fila. Para
usar outra execução, acrescente `--plano caminho\plano-personagens.json`.

Para uma pasta com homens e mulheres, forneça `--metadata metadata.json`, por
nome de arquivo ou pelo nome sem extensão, em vez de atribuir o mesmo gênero à
pasta inteira:

```json
{
  "avatar_cozinha.png": {"gender": "female", "tags": ["cozinha", "adulto"]},
  "avatar_escritorio.png": {"gender": "male", "tags": ["escritorio", "adulto"]}
}
```

## Conjuntos e distribuição de prompts

O arquivo final inclui o nome completo cadastrado do avatar e o conjunto de
prompts: `AV20261021_16_mulher_01__v1_esposa__40s.mp4`. O ID interno continua
no tracking das cenas. Entregas anteriores mantêm seus nomes e recibos.

No teste, todos recebem o mesmo conjunto, com cinco cenas diferentes. Em produção
é possível fornecer vários conjuntos, cada um representando um áudio dividido em
cinco frases. Cada prompt pode ser uma string ou um objeto com `text` e `spoken`
(frase esperada para QA posterior). Não há geração de TTS neste fluxo: o áudio é
gerado pelo Flow usando a voz atribuída ao personagem.

Formato completo: `automacao-personagens/exemplo-prompts.json`.

- `prompt_sets`: textos e compatibilidade de cada conjunto.
- `genders`: restringe o conjunto a `female`, `male` ou ambos.
- `required_tags`: todas as tags exigidas precisam existir no personagem.
- `assignments`: fixa explicitamente `id_do_personagem → id_do_conjunto`.
- `distribution.mode: cycle`: alterna os conjuntos compatíveis.
- `distribution.mode: random`: sorteia entre conjuntos compatíveis; `seed` permite
  repetir a distribuição em uma nova preparação.
- `distribution.mode: quota`: usa cotas exatas, por exemplo cinco personagens para
  `audio_x` e cinco para `audio_y`. As cotas precisam somar o total de personagens.

Os IDs dos personagens vêm dos nomes dos retratos sem a extensão. A atribuição
final consta em `assignments` no plano; o modo de distribuição não é executado
novamente durante a geração. Uma nova atribuição ou outro conjunto exige uma nova
execução depois que a fila começou.

## Tracking e recuperação

Cada cena registra personagem, voz no cadastro, conjunto, número 1–5, prompt
exato, hash do texto, tentativa, inventário anterior, recibo do macro, ID do Flow,
download, hash do MP4 e estado. A montagem registra os hashes das cinco cenas.

Arquivos principais da execução:

- `plano-personagens.json`: entradas, vozes e atribuições fixas.
- `characters/*.json`: recibos do upload e cadastro, com ID do personagem.
- `estado-personagens.json`: fila persistente, cenas e entregas.
- `native/<cena>/prompt.txt`, `recibo.json`, `macro.log`: envio nativo.
- `clips/`, `downloads/`, `frames/`: clipes, recibos e últimos frames.
- `RELATORIO-PERSONAGENS.md` e `.json`: andamento e pendências.
- `controlador.log` e `processo.json`: processo independente.
- `alertas/*.json`: solicitação de revisão e recibo da notificação ao Codex.
- `revisoes/*.json`: decisão do agente, aplicada pela própria fila.

Limites: concorrencia configuravel, intervalo mínimo de um segundo entre envios,
prazo por macro/render e uma trava que exclui a fila de receitas. O prazo do macro
pode ser aumentado em `limits.native_timeout` antes de iniciar para prompts longos.

Se houver clique possivelmente efetuado, a cena nunca volta automaticamente para
`pending`. A retomada procura o vídeo existente pelo inventário anterior e prompt
exato. Um ID ambiguo ou ausente fica em `uncertain`. Com teto local, interrompe
novos envios; no modo sem teto, fica separado para reconciliacao, sem reenvio,
enquanto as outras cenas continuam.
Upload atribuído sem ID também não é reenviado. Recusas confirmadas e falhas de
áudio geram uma solicitação de revisão. Um arquivo entregue sem recibo compatível
não é sobrescrito.

### Alertas e até três tentativas

Por solicitação do usuário, uma cena com recusa confirmada, áudio ausente ou fala
divergente é enviada para revisão do agente. O alerta guarda personagem, motivo,
prompt, fala original e tentativas restantes. `codex queue --thread ...` notifica
a mesma conversa, cujo ID fica em `notificacao.json`; o envio tem recibo próprio.
Por solicitação do usuário, os alertas automáticos estão desativados em
`automacao-personagens/notificacoes.json` (`enabled: false`). Essa configuração
vale para todas as execuções de personagens e não é reativada ao iniciar a fila.
Os eventos de revisão continuam registrados localmente, sem notificar a conversa.
Se Codex ou a conversa não estiverem disponíveis, o alerta fica no disco como
pendente e a fila não finge que o agente foi avisado.

O agente pode corrigir ambiguidades da descrição visual ou instruções técnicas
para conteúdo permitido. A frase falada é imutável: a revisão só entra se o texto
entre as aspas do bloco de diálogo for exatamente igual, incluindo a pontuação.
Revisão que altere a fala é rejeitada pelo código. Não se alteram mecanismos de
segurança, login ou verificações do serviço.

O agente devolve um arquivo de texto com o prompt completo revisado:

```powershell
python automacao-personagens\cli.py revisar-cena --cena avatar_01__audio_x__04 --arquivo prompt-revisado.txt
```

A fila lê a decisão e usa novamente **o macro nativo**; o agente revisor não clica
em gerar. Para compartilhar um esclarecimento visual com cenas ainda bloqueadas
pelo mesmo prompt, há `--compartilhar-bloqueadas`. A decisão e a fala são
conferidas para cada destinatário. Cenas concluídas não são reiniciadas sem uma
reprovação explícita de qualidade.

Se a inspeção encontrar legenda ou outro defeito visual em uma cena já baixada,
use `sinalizar-qualidade --cena ID --motivo DESCRICAO` para enviar a reprovação à
fila sem interromper outras gerações. O hash do clipe é conferido antes de aplicar;
a reprovação aguarda uma montagem em andamento para preservar seu recibo.
Para revisão com a fila parada,
pare a fila e use `reprovar-qualidade --cena ID --motivo DESCRICAO`. A cena volta
para revisão, respeitando o mesmo limite de tentativas. Se já houver montagem,
ela é preservada em `_revisoes` na pasta de entrega; a nova montagem só é feita
depois da correção. O comando recusa arquivar arquivos cujo hash tenha mudado.

O limite é de **três tentativas totais por cena**, contando a primeira. Quando uma
cena esgota o limite, o avatar inteiro é marcado como `discarded`; os clipes e
recibos anteriores são preservados, nenhuma montagem incompleta de 40s é entregue
para ele e a fila segue para o próximo avatar. Downloads de tentativas diferentes
têm nomes próprios e nunca substituem o clipe anterior.

Enquanto aguarda revisão, a fila continua cenas elegíveis de outros personagens.
Envios incertos precisam ser reconciliados antes de qualquer repetição. Uma
recusa visível sem ID pode ser conferida com `reconciliar-falha`, que recupera o
texto pelo botão **Reutilizar comando**, sem clicar em **Tentar de novo**.
Se o agente registrar `hold_retry` após investigar um envio incerto, somente as
outras cenas continuam. O envio isolado continua sendo consultado e não volta
automaticamente à fila de geração. Sem confirmação, o avatar fica pendente e não recebe
montagem de 40s; o relatório não o apresenta como entregue ou descartado.

Dentro das três tentativas autorizadas, o agente pode registrar uma revisão
manual após ausência persistente por mais de dez minutos e duas novas consultas
sem vídeo correspondente, separadas por dez segundos. O recibo anterior continua
marcado como não confirmado; uma reserva dessa tentativa ocupa uma vaga até o
prazo de render do plano. A nova tentativa usa prompt revisado com fala idêntica,
e nunca é um reenvio automático sem investigação. A evidência fica no JSON da
execução. Se houver candidato no inventário, deve-se reconciliar seu ID.

Um ID conhecido que desaparece do inventário e retorna código 5 na consulta
de mídia por ao menos dez segundos segue para revisão como recurso removido.
Isso combina duas evidências, evitando classificar um atraso inicial como falha.

O transporte usa o comando oficial
[codex queue](https://learn.chatgpt.com/docs/developer-commands#codex-queue),
verificado com envio real a esta conversa em 21/10/2026.

Esc, perda de foco, sessão bloqueada, login/verificação humana, atividade incomum,
configuração divergente ou créditos não confirmados em zero interrompem o macro.
O arquivo `PARAR` permanece após a parada; remova conscientemente para retomar.

## Qualidade e teste de 21/10/2026

### Velocidade e vagas de geração

A fila repoe vagas segundo `max_rendering`. O padrao do plano e tres;
`operacao.json` pode sobrescrever com um inteiro positivo ou `null` para remover
o teto local sem alterar o hash do plano. Nesta leva, por pedido do usuario,
o valor e **null**, sem espera programada entre envios. Os limites impostos
pelo Flow continuam valendo; um botao de envio desabilitado e aguardado sem clique.
Confirmação de envio já ocupa uma vaga. Um envio incerto isolado também reserva
uma vaga até a reconciliação, pois ainda pode estar em processamento no serviço.
No fim do lote ou durante bloqueios/revisões pode haver menos vídeos em andamento.

Downloads usam um trabalhador separado, sem segurar o inicio do proximo macro.
Conferência de áudio, transcrição e montagem usam outro trabalhador local separado;
esses trabalhos não bloqueiam o próximo envio. O estado `checking` é persistido
e retomado sem gerar novamente. Os subprocessos locais ficam ocultos para não
roubar o foco do macro. O intervalo mínimo de envio é de um segundo e a consulta
normal acontece a cada dois segundos; o preparo nativo também ocupa tempo.

O macro de personagens digita blocos de 128 caracteres por teclado nativo,
confere o texto integral e mantém as travas de foco, projeto e personagem.
O intervalo inicial é de 3 ms por tecla, a velocidade do fallback anterior. Se o
campo não preservar o texto, repete somente a digitação a 4 ms, sem novo clique
de geração nem tentativa consumida. Usar a velocidade estável na primeira
passagem evita o tempo de redigitação observado a 2 ms.
O cursor percorre curvas suaves e variadas até cada alvo em cerca de 190–400 ms,
com aceleração e desaceleração. O clique continua condicionado à conferência do alvo,
da posição, do foco e do projeto. Se o editor se deslocar antes do clique,
somente esse campo é localizado novamente, até três vezes, sem envio.
As pausas curtas foram reduzidas para até 80 ms. Há uma configuração inicial
por envio; a segunda abertura/conferência antes de clicar foi removida por
solicitação do usuário. A seleção de modelo é reaproveitada quando confirmada.
A captura extra de respostas de rede fica desligada; para diagnóstico pode ser
ativada no plano com `diagnostics.capture_responses: true`. O inventário e os
recibos continuam responsáveis pela identificação dos vídeos.

Teste real sem envio em 21/10, após validar um prompt longo: configuração 5,421s,
personagem 4,813s, digitação 5,375s, preparação total 15,609s.
Um envio real anterior, com prompt mais curto, foi confirmado em 14,390s.
O macro registra `PERFORMANCE` no log
e o controlador preserva os tempos por tentativa. Esses números medem o preparo,
não o tempo de renderização do Flow.

Validação técnica verifica arquivos de oito segundos, 720×1280, decodificação,
hashes e montagem de quarenta segundos. Ausência de áudio e divergência da fala
impedem a entrega e solicitam revisão para nova geração. A transcrição local é
comparada ao roteiro; folhas de contato a 2 fps apoiam a inspeção visual.
Selecionar a mesma voz no personagem não garante sozinho que
o modelo pronuncie todas as frases corretamente ou mantenha o timbre.

Teste autorizado: projeto
`https://flow.google.com/u/1/project/e0edef62-354f-44ea-b8d5-e2730ae157b9`,
cinco retratos de `S:\@Organico (S)\21 outubro - Testes Avatar\Avatares`,
entrega em `S:\@Organico (S)\21 outubro - Testes Avatar\Videos Avatares Prontos`.
Plano e resultados atuais:
`execucoes-personagens/20261021-teste-avatares/RELATORIO-PERSONAGENS.md`.

Os cinco personagens foram cadastrados pela interface, cada um com voz feminina
distinta. A preparação real do macro passou sem envio antes de iniciar a fila.
Vinte e dois testes locais passaram, incluindo cotas, gênero/tags, não repetição de
clique incerto, persistência, montagem real de 40s, retomada do controlador,
notificação/revisão, fala imutável, descarte após três tentativas e proteção contra
sobrescrita. Os 28 testes existentes da fila de receitas também passaram.
O relatório da execução informa quais gerações e entregas realmente concluíram.

Resultado do teste: **5/5 avatares entregues**, 25 cenas e cinco montagens de 40s,
sem avatar descartado. A auditoria final conferiu arquivos no destino, hashes,
duração, áudio, modelo e referência do personagem nas 25 cenas. Os prompts e as
revisões preservaram a fala original. Uma transcrição reconheceu “gonna” em vez
de “going to”; há pequenas dissoluções/ghosting em algumas caudas. As observações
estão em `AUDITORIA-FINAL.json`, `REVISAO-VISUAL.json` e no relatório da entrega.
A identidade e continuidade da voz ainda dependem de audição humana.

Na leva `20261021-ed-30-v1-v2-v3`, os 30 personagens já cadastrados recebem dez
atribuições de cada versão do arquivo `prompts_avatares_ed_3_versoes.md`.
As entregas ficam em `Videos Avatares Prontos/Lote 30 - 3 versoes`, com o nome
completo do avatar no arquivo. O plano, as tentativas e as revisões permanecem
nessa pasta de execução, separados do teste inicial e das receitas.

Por solicitação do usuário, essa leva permite repetir pelo fluxo normal cartões
de geração recuperáveis que exibem “atividade incomum”. A autorização fica em
`operacao.json` (`retry_recoverable_error_tiles`). O aviso precisa estar dentro
de `flow-error-tile`; avisos globais e verificações humanas continuam exigindo
intervenção. Antes de repetir, a interface deve confirmar exatamente o prompt
e o retrato do cartão que falhou. Só essa falha de serviço confirmada permite
reusar o prompt idêntico; recusas de conteúdo continuam no processo de revisão.
O limite de três tentativas e a preservação da fala continuam ativos. Os 55
testes locais atuais cobrem também essa distinção, o nome final e a inspeção
visual assíncrona.

Com `visual_controls: true` em `operacao.json`, pressionar **+ duas vezes em até
500 ms** pausa mouse, teclado e novos comandos. Repetir **++** retoma. Aceita o
`+` do teclado numérico e `Shift` + `=`. Teclas injetadas pelo macro e a repetição
automática de uma tecla segurada não acionam o atalho. A pausa é persistida em
`PAUSADO`, não consome o prazo do macro e não cancela renderizações já enviadas.
O arquivo `operador.json` registra o listener, a pausa e a atividade visual.
O listener usa uma thread exclusiva com `GetMessage`; a animacao usa outra
thread, para que o intervalo entre frames nao atrase as teclas do macro.

Durante esperas, o cursor faz uma animação suave dentro do campo de prompt, sem
cliques. Ela para antes de qualquer operação nativa e quando o Flow perde o foco.
Cadastros íntegros com a mesma imagem, voz e ID são reaproveitados sem abrir
novamente trinta telas na retomada. A fila repõe vagas assim que os resultados
liberam capacidade, respeitando a concorrencia configurada.

## Gravar o movimento do usuário

Abra `Gravar-Movimentos-Personagens.cmd`. A produção precisa estar parada: o
gravador segura a mesma trava do controlador enquanto sua janela está aberta.
A pausa existente é preservada ao fechar o gravador.
O gravador aceita a raiz e as telas internas do mesmo projeto e da mesma conta,
inclusive URLs com parâmetros de seleção acrescentados pelo Flow.

1. Escolha **Geral** para começar. Pressione **F8**: há cinco segundos para se
   preparar e depois dez segundos de captura. Faça seus trajetos e clique no
   final de cada aproximação. **Esc** cancela a tomada atual sem salvar.
2. Repita F8 até obter **5/5 versões**. Cada tomada começa somente quando você
   pede. **Refazer última** arquiva a versão anterior e libera a vaga.
3. Se desejar gestos próprios para certos controles, repita nas categorias
   **Configuração**, **Texto**, **Enviar** e **Espera / dança**. Essas categorias
   são opcionais; Geral serve como base para todas.
4. **Ver movimento no Flow** demonstra a última gravação movendo o cursor,
   sem executar cliques. Feche o gravador para liberar a fila.

Por padrão, cliques durante a captura são **marcadores de trajeto** e não
acionam os botões do Flow. Isso permite ensaiar o envio sem gerar um vídeo.
Marque **Aplicar cliques na tela durante a gravação** apenas quando quiser
operar a interface enquanto grava, por exemplo para abrir configurações.
O gravador registra posições, tempos e marcadores de clique; não grava teclas,
áudio nem vídeo da tela.

Arquivos: `automacao-personagens/movimentos-usuario/catalogo.json` e um JSON por
tomada. A escolha das versões 1→2→3→4→5→1 persiste entre processos em
`selecao.json`. Categorias específicas têm preferência; categorias vazias usam
Geral. As aproximações aos cliques são adaptadas à distância e direção do alvo
atual, preservando a curva e o ritmo relativo; deslocamentos duram de 0,16 a 0,65 s.
Os cliques reais continuam sendo executados e verificados pelo macro no alvo
atual. A espera reproduz o trajeto completo na área do Flow, sem cliques.
Enquanto não houver gravações, permanece disponível a animação gerada.

Para cadência de produção, `operacao.json` aceita `submission_interval_seconds`
(nesta leva: **0**, sem espera programada). O macro prepara a próxima cena antecipadamente e aguarda
o prazo antes de enviar. O relógio parte de `clicked_at`, registrado junto ao
clique anterior, sem somar o tempo da confirmacao posterior, inclusive
após retomadas. Nesta leva nao ha teto local de vagas. Se o Flow bloquear o
botao ou a interface/servico estiver lento, o intervalo pode ultrapassar a meta. As consultas
de andamento são paralelas; a conferência inicial lê as configurações em uma
única árvore. A digitação permanece em 3 ms por tecla, com fallback de 4 ms e
conferência do texto completo. A reprodução do mouse usa prazos absolutos para
evitar acumular o tempo das chamadas nativas em cada ponto gravado.

O ponto aprovado anterior, com intervalo de 25 s, esta salvo em
`../backups/20261021-233800-personagens-aprovado-25s/`. O ZIP, os 961 arquivos e
seus hashes foram verificados. `LEIA-RESTAURACAO.md` descreve como restaurar o
codigo/configuracao sem sobrescrever o tracking mais recente. A unica alteracao
funcional inicial posterior a esse ponto foi permitir `submission_interval_seconds: 0`.
O preparo, a digitacao e os controles do Flow continuam levando seu tempo normal.

Na otimizacao seguinte, inventario, poll e ativacao da aba foram reunidos em
uma unica chamada `snapshot`, mantendo um inventario novo antes de cada preparo.
Downloads passaram para segundo plano. O proximo macro nao espera terminar um
download; `handoff_seconds` e `browser_cycle_seconds` nas tentativas registram
o tempo real dessa passagem. Nao existe pausa fixa entre macros, mas as consultas
ao navegador e a abertura do processo ainda consomem tempo. O teste real da
consulta unificada levou 2,9 s; download e consulta em paralelo tambem passaram.

Antes do envio, o macro dispensa tooltips com Esc: os trajetos pelas miniaturas
podem abrir o balão “Favorito” sobre o compositor. Se o hit-test do Windows
retornar um painel, uma consulta de leitura confirma o botão realmente sob
o ponto, o texto exato e a conta/projeto. O clique continua sendo nativo e só
ocorre após a confirmação; o recibo de intenção nasce imediatamente antes dele.

A aproximação de envio usa os limites do painel do compositor, identificados
pela acessibilidade. A curva gravada fica contida nessa área; os últimos 64 px
chegam pela esquerda, em 120 ms, sem ultrapassar ou contornar o botão. Essa
restrição vale somente para o envio e preserva a alternância das gravações.
O fechamento de tooltips também aguarda a animação terminar antes da conferência.

A danca ociosa fica na intersecao do editor com o painel visivel do compositor,
excluindo botoes e a galeria. Se essa area nao for reconhecida, a animacao para.
Isso evita abrir previews continuamente: no diagnostico, 12 hovers fizeram os
players carregados crescerem de 3 para 13. Nao foi reproduzido o preto persistente
nesse teste. Na validacao da nova espera, 229 frames ficaram no editor, sem novos
players (17 antes/depois) e sem erros de midia. Nao se regenera um video apenas
porque a miniatura ou preview aparece preto; o arquivo passa pelo QA normal.

Reservas de envios sem ID podem ser liberadas apos o prazo de renderizacao e
conferencia de ausencia de resultado. A prova `reservation_release` identifica
a tentativa e registra `expires_at` e `absence_confirmed_at`. A cena continua
incerta, sem reenvio autorizado, mas deixa de ocupar uma vaga para sempre.
Uma nova tentativa nao herda a liberacao da anterior. Resultados tardios ainda
sao reconciliados normalmente pelo inventario.

Testes: `python -m unittest discover -s automacao-personagens -p "test_*.py"`.

```powershell
. .\env.ps1
python -m unittest discover -s automacao-personagens -p test_personagens.py -v
```
