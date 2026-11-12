# 06 — O funil orgânico: comentário → DM → oferta

O reel não vende. Ele **coleta**. A venda acontece na DM e na bridge.

```
reel  →  comentário com a KEYWORD  →  DM automática com o link  →  bridge  →  oferta
```

Por que passar pela DM em vez de pôr o link na bio: **link no perfil derruba alcance
orgânico**. Na DM ele não custa distribuição nenhuma.

---

## A keyword

Uma palavra, fácil de digitar, ligada ao conteúdo. `yes` é o padrão do nicho e converte;
uma palavra temática (`horse`, `recipe`) é mais memorável e serve de rastreio.

**Regras:**

- **Uma keyword por página.** Se você tem várias páginas, keywords diferentes servem de
  A/B natural — e permitem saber de qual página veio o lead sem instrumentação nenhuma.
- Na **fala** vai capitalizada normal (`Yes`). CAIXA ALTA faz o TTS soletrar.
- Na **legenda queimada** vai em CAIXA ALTA, gigante e amarela, com **≥0,75s** na tela.
- Na **legenda do post** vai em CAIXA ALTA.

## 🔴 `Follow me first` antes da keyword

Quem comenta **sem seguir** a página recebe apenas uma *Private Reply* — uma resposta
única, mais fraca, que não abre conversa. Quem já segue recebe DM de verdade.

Por isso o CTA é sempre nesta ordem:

> *"Follow me first, then comment YES and I'll send it to you today."*

E ele precisa estar **na fala**, não só na legenda do post. Um vídeo nosso saiu com o
`follow me first` só no texto — funciona pior, e é um erro de roteiro, não de copy.

---

## A bridge

Uma página estática, sua, entre o reel e a oferta. Ela existe por três motivos:

1. **A plataforma não gosta de link direto pra checkout.** A bridge é neutra.
2. **Ela entrega o que você prometeu** (a receita, a aula) antes de pedir algo.
3. **É onde você mede.** Sem ela, você só sabe quem comentou — não quem clicou.

🔴 **A bridge tem que estar no ar ANTES do primeiro post.** Sem URL pública o comentário
chega e não há o que mandar — e a primeira hora do post é a que decide a distribuição.

## A automação comentário → DM (a peça que faz o funil rodar sozinho)

O funil é: a pessoa comenta a **keyword** no reel → recebe uma DM automática com a **bridge** → clica → oferta.
Sem a automação, você responderia comentário por comentário na mão — não escala e morre no 2º dia. Duas
opções, as duas funcionam; escolha a que a sua conta permitir:

**Opção 1 — automação nativa da Meta (grátis, sem app de terceiro).** No Instagram profissional (Criador ou
Empresa) e nas Páginas do Facebook, a própria Meta tem "respostas automáticas": *Meta Business Suite → Caixa de
Entrada → Automações → "Comentário → mensagem"* (o nome exato muda com o app; procure por "automação",
"respostas automáticas" ou "comentar para receber"). Você define: (a) a **palavra-chave** — a keyword da página,
exatamente como aparece no vídeo; (b) a **mensagem** — o texto curto + o link da bridge; (c) responder também o
comentário publicamente (opcional; ajuda o alcance). Ative pra "todas as publicações" ou só pros reels.
Limite: a nativa é mais simples e mais restrita (uma mensagem, sem sequência).

**Opção 2 — ferramenta de automação de DM (ManyChat e similares).** Plano gratuito cobre uma página no começo.
Conecte a conta → crie um gatilho "comentário no post contém [keyword]" → ação "enviar DM" com a bridge → (opcional)
2ª mensagem se a pessoa não clicar em X horas. Vantagem: sequência, tag por vídeo, estatística de clique. Use
quando a página tiver volume.

**Regras que valem nas duas:**
- **Configure e TESTE antes do primeiro post** (comente você mesmo de outra conta e veja a DM chegar). Post no ar
  sem automação = comentários com a keyword sem resposta = funil morto no dia 1.
- **A keyword da automação é a MESMA do vídeo, letra por letra.** Keyword no reel "PLANO" e gatilho "plano" pode
  falhar dependendo da ferramenta — configure sem distinção de maiúscula e sem acento.
- **Filtro de palavrão/comentários ocultos DESLIGADO** — ligado, ele manda o comentário com a keyword pra
  revisão e a automação nunca vê (é o erro silencioso mais comum; ver `02-PAGINA-E-PERSONA.md`).
- **`Follow me first` opcional, nunca obrigatório** no começo (seção acima) — cada passo a mais derruba metade.
- **Uma automação por página, uma keyword por página.** Duas páginas com a mesma keyword em contas diferentes é
  ok; a mesma página com duas keywords confunde a métrica.
- A DM leva **só a bridge** (link + 1 frase). Preço, argumento e prova ficam na página de destino — DM longa cai
  em spam.
- Rastreie por vídeo (seção seguinte): a automação diz quantos comentaram; a UTM da bridge diz quantos clicaram.

## Rastreio: sem isso você mede metade do funil

O funil tem quatro degraus e a maioria mede dois:

| degrau | mede? |
|---|---|
| viu o reel | ✅ nativo |
| comentou | ✅ nativo |
| **abriu a bridge** | ❌ sem instrumentação |
| **clicou pra oferta** | ❌ sem instrumentação |

Sem os dois últimos você não sabe **qual criativo gera venda** — só qual gera comentário.
E um vídeo pode dar 10 comentários e zero clique.

**Duas camadas, as duas de custo zero:**

1. **Subid por vídeo.** A DM manda `/bridge?v=v07`, e um script na bridge reescreve o
   subid do link de afiliado pra incluir o id do vídeo. A plataforma de afiliado passa a
   contar **clique e venda por vídeo**. Sem o parâmetro, o subid padrão é mantido — nenhum
   link quebra.
2. **Analytics sem cookie** (GoatCounter e similares) — pageview + evento de clique no
   CTA. Sem cookie significa **sem banner de consentimento**.

⚠️ Placeholder esquecido não conta nada e não avisa. Confira que o código real está nas
páginas antes de considerar instrumentado.

---

## Cadência de publicação

- **1 post por página por dia**, horário fixo.
- ⛔ **Nunca duas páginas suas no mesmo horário.**
- **Estoque mínimo de 3 vídeos** antes de começar a publicar.

**Por que ritmo importa:** o multiplicador de distribuição compara com a **média
histórica da própria página**. Três posts num dia e nenhum no seguinte é rajada e
silêncio — a página não constrói média. Um por dia constrói.

⚠️ Honestidade sobre esse ponto: é hipótese plausível e barata, apoiada no histórico —
não é fato isolado em teste controlado.

---

## O primeiro post define a régua

Página nova não tem média histórica, então **o primeiro vídeo é que crava a régua** que
todos os próximos vão ter que superar. Publicar um vídeo fraco ou curto primeiro custa
caro depois.

✅ **Estreie com o melhor vídeo do estoque**, não com o mais antigo.

---

## ✅ Checklist antes do primeiro post

1. Bridge **no ar**, URL pública testada?
2. Automação comentário→DM configurada **com a keyword desta página**?
3. Filtro de palavrão **desligado** (senão o comentário some e o funil morre calado)?
4. Rastreio de clique instalado, com o código real e não o placeholder?
5. O vídeo de estreia é o **melhor** do estoque?
6. `Follow me first` está **na fala**, não só na legenda?
7. A keyword aparece na legenda queimada com tempo de leitura?
8. Rótulo de IA ligado?
