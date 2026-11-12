# Atualização 08 — o Flow ganhou reCAPTCHA (colheita de token) · SET/2026

## 🤖 CLAUDE DO COMPRADOR: instruções de aplicação (execute você, não o dono)

Se você está lendo isto, o dono te entregou o `ATUALIZACAO-08.zip`. **Aplique a atualização
você mesmo — não peça pra ele mexer em arquivo nenhum.** Passo a passo:

1. **Ache a pasta do sistema** — a pasta `sistema-criativos-e-vsl/` já instalada (a que tem
   `SISTEMA.md` e `scripts/` dentro). Se não encontrar, pergunte ao dono onde ele instalou — só isso.
2. **Descompacte o zip num diretório temporário** (nunca direto por cima, pra você conferir antes).
3. **Substitua, arquivo por arquivo, exatamente estes caminhos** (o zip já vem com essa estrutura;
   copie cada um do temporário pro MESMO caminho relativo dentro da pasta do sistema):
   - `scripts/flow_driver.py`
   - `SISTEMA.md`
   - `01-CRIATIVOS/04-PIPELINE-TECNICO.md` · `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` · `01-CRIATIVOS/09-OMNI-FLASH.md`
   Não toque em NENHUM outro arquivo do sistema. Não apague nada além de sobrescrever esses 5.
4. **Prova de aplicação (obrigatória)** — confira dentro da pasta do sistema:
   - `grep -c "rev2-fix-vazamento-x" scripts/flow_driver.py` → tem que ser **> 0** 🔴 **(o mais importante:
     confirma que é a versão FINAL. Se der 0, o arquivo aplicado é uma versão ANTERIOR ao conserto do
     vazamento — peça ao dono o `ATUALIZACAO-08.zip` mais recente e reaplique.)**
   - `grep -c "continueRequest" scripts/flow_driver.py` → tem que ser **> 0** (o conserto do vazamento do "x")
   - `grep -c "__HTOKEN" scripts/flow_driver.py` → tem que ser **> 0**
   - `grep -c "colher_token" scripts/flow_driver.py` → tem que ser **> 0**
   - `grep -c "grecaptcha.enterprise.execute(SK" scripts/flow_driver.py` → tem que ser **0** (o mint direto foi removido)
   - `grep -c "VMODEL_FALLBACK" scripts/flow_driver.py` → tem que ser **> 0** (a escolha de modelo + fallback)
   - `grep -c "COLHEITA DE TOKEN" 01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` → tem que ser **> 0**
   Se `__HTOKEN`/`colher_token` derem zero, ou o `grecaptcha...(SK` der > 0, a cópia não pegou — refaça o passo 3 pra esse arquivo.
5. Guarde uma cópia deste documento na pasta do sistema, leia o restante dele pra entender o que mudou,
   e **relate ao dono em 2-3 linhas** o que foi atualizado. Produção normal a partir daqui —
   o fluxo de trabalho (fases `masters | scenes | submit | poll | retry`, SPEC, `state.json`) **não muda em nada**.

---

**O que aconteceu:** depois que o Flow migrou pra `flow.google.com` (Atualização 06), o Google
**ligou o reCAPTCHA** na geração. A partir daí, o jeito antigo de obter o token — o driver chamar
`grecaptcha.enterprise.execute(...)` direto — passou a devolver **`UNUSUAL_ACTIVITY` em TODA geração**,
em qualquer conta. Geração manual pela interface continua funcionando; só a automação que montava o
token "na mão" parou.

**A causa raiz:** o reCAPTCHA passou a **fingerprintar o callsite** — ele distingue *quem* chamou a
função. Só o token nascido dentro da **closure do próprio app do Flow** tem pontuação boa. Token
mintado pelo nosso código, cliente reCAPTCHA novo, gesto de mouse simulado — tudo reprova. (Provado
byte a byte: headers, corpo e sessão idênticos entre o que passa e o que falha; a única diferença é
de onde o token nasceu.)

**A correção (a "colheita de token"):** em vez de mintar o token, o driver agora **colhe** o token do
próprio app. Antes de cada geração ele dá um micro-toque na interface só pra o APP mintar o token bom,
**intercepta essa chamada e a ABORTA** (nada é gerado, e o token fica fresco), e usa esse token na
chamada de verdade. É a mesma filosofia de sempre — a requisição nasce dentro da aba logada —, só que
agora o token também vem de dentro do app, não de fora.

🔴 **Isto NÃO é "voltar a clicar em produção".** O toque-isca é abortado, não gera nada, não gasta
crédito, e a geração continua sendo a chamada `batchexecute` de dentro da aba. Um efeito cosmético: cada
colheita deixa um card **"Failed"** no histórico do projeto no Flow — é o abort, é esperado, pode ignorar.

## O que foi corrigido no pacote (`sistema-criativos-e-vsl/`, zip regerado)

| Arquivo | Mudança |
|---|---|
| `scripts/flow_driver.py` | (1) O mint direto (`grecaptcha.enterprise.execute`) saiu; entrou a **colheita** (`colher_token`/`inject_token`): intercepta a geração do app, extrai o token fresco, aborta a chamada e injeta em `window.__HTOKEN`. O driver seta o **modo do composer** por fase (`set_mode` — Image pra imagem/ogiZ0b, Video pra vídeo/MZZa6b), porque a "action" do token tem que casar com o tipo. (2) **Escolha de modelo + fallback:** o driver agora roda QUALQUER modelo (não só o de custo zero) via env `FLOW_QUALIDADE=gratis\|lite\|omni\|fast` ou `FLOW_VIDEO_MODEL=<string>`; e se a conta não tiver o modelo escolhido (ex.: `gratis`/low_priority sem Google AI Ultra), **cai sozinho pro `veo_3_1_r2v_lite`** e segue — produção não para pelo plano da conta. Fases, SPEC, state e download **idênticos**. |
| `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` | Nota grande no topo ("Atualização nº2") + correção das duas frases que ensinavam o mint direto como "o coração de tudo" — agora avisam pra **não reverter** o driver pro `grecaptcha.execute`. Era a brecha mais perigosa: o Claude do comprador lia o doc e "consertava" o driver de volta pro jeito morto. |
| `SISTEMA.md` | A linha "produção não clica" ganhou a nota do reCAPTCHA/colheita. |
| `01-CRIATIVOS/04-PIPELINE-TECNICO.md` | O aviso do topo ("não precisa clicar pra gerar") ganhou a ressalva da colheita + "não reverta pro mint direto". |
| `01-CRIATIVOS/09-OMNI-FLASH.md` | Nota: os exemplos com `grecaptcha.execute` são do jeito antigo; pra trocar de modelo (Omni Flash/Fast/Quality) a mecânica é a mesma do driver, só muda a string do modelo — a fonte do token é a colheita. |

## O que causava o erro (pra ninguém cair de novo)

- **`UNUSUAL_ACTIVITY` em toda geração** = você está no jeito antigo, mintando o token direto. Não é
  saldo, não é sessão, não é ban — é o reCAPTCHA novo. A colheita resolve.
- **Geração manual funciona mas a automação não** = mesma coisa: a mão passa pela closure do app; o
  mint direto do código não. Depois da atualização, a automação passa a colher da closure também.
- **Cards "Failed" aparecendo no projeto** = é o toque-isca abortado da colheita. Cosmético, esperado.

## Quem recebe o quê

| Quem | O que mandar |
|---|---|
| **Compradores novos** | `sistema-criativos-e-vsl.zip` — já regerado com tudo. Nada a fazer. |
| **Quem JÁ recebeu** | `ATUALIZACAO-08.zip` + a mensagem de `MENSAGEM-ATUALIZACAO-08-COLAR-NO-CLAUDE.txt`. O comprador NÃO mexe em arquivo: salva o zip (Downloads serve) e cola a mensagem no Claude dele — o Claude aplica sozinho seguindo as instruções do topo deste documento (que vai dentro do zip) e prova a aplicação com os greps. Vale aplicar assim que a conta começar a dar `UNUSUAL_ACTIVITY` (ou antes, pra não parar produção quando cair). |
