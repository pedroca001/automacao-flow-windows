# 02 — Página e persona

## A persona carrega a promessa sem falar nada

O trabalho mais barato de copy que existe: escolher uma persona que **já comunica o
enquadramento do nicho antes da primeira palavra**.

Exemplos reais de páginas que escalam:

| persona | o que ela comunica de graça |
|---|---|
| mulher de comunidade tradicional/religiosa | "receita antiga, natural, sem indústria" |
| esposa 15-20 anos mais nova que o marido | prova social do resultado, sem afirmar nada |
| avó com caixa de receitas | tradição, herança, "isso existe há décadas" |
| enfermeira aposentada | autoridade sem título formal |

> A concorrente forte do seu nicho já escolheu uma dessas. **Não copie a mesma** — pegue
> a vizinha semântica. Mesmo enquadramento, rosto diferente.

## Nome da página decide o visual da identidade

Regra que custou um retrabalho pra descobrir:

- Página com **nome de pessoa** (`Nome Sobrenome`) → **rosto** na foto de perfil.
- Página com **nome de marca** (`Morning Kitchen Ritual`) → **logo**.

O erro foi usar rosto de avatar numa página de marca: fica um híbrido que não lê como
pessoa nem como negócio.

## Identidade visual custa zero

Perfil (1024×1024) e capa (1640×624) se renderizam **localmente**, em HTML + um
navegador headless tirando screenshot de um `<div>`. Sem crédito, sem ferramenta paga,
e regerar é instantâneo quando algo muda. O comando de render (Chrome headless + `--screenshot`, `--window-size` no tamanho exato) está em `01-CRIATIVOS/04-PIPELINE-TECNICO.md`, Parte 3 ("Pipeline B") — mesma técnica; peça pro Claude "monta o HTML do perfil e da capa e renderiza com o headless" e confira o PNG antes de subir (texto cortado atrás de nada, tagline legível no celular).

⚠️ **A capa promete um objeto.** Se a tagline diz *"same jar, every morning"* e os vídeos
passam a mostrar uma embalagem impressa, a capa virou mentira. Toda vez que o formato do
criativo mudar, releia a capa.

---

## Campo a campo

| Campo | Regra |
|---|---|
| **Nome** | pessoa → nome próprio comum do país-alvo · marca → 2-3 palavras descritivas |
| **Categoria** | `Blog pessoal`. Categoria de negócio pede endereço e muda o que a plataforma cobra de você |
| **Bio** | curta, primeira pessoa, com emoji. ⛔ **sem CTA, sem link** |
| **Cidade** | uma cidade real do país-alvo. **Diferente em cada página sua** |
| **Website** | ⛔ **vazio** |
| **Link na bio** | ⛔ **vazio** |
| **Filtro de palavrão** | ⛔ **DESLIGADO** |

### Por que cada proibição existe

- **Link em website/bio** marca o perfil como comercial e derruba o alcance orgânico. O
  link vive na DM, que é onde ele não custa distribuição.
- **Bio vazia** é a marca do cluster que performa mal. Ter bio importa; ter bio longa não.
  O campo **corta em ~255 caracteres, em silêncio** — já truncou CTA no meio.
- 🔴 **Filtro de palavrão ligado esconde o comentário com a keyword.** O funil inteiro
  depende de você VER a palavra que a pessoa comentou. Com o filtro ligado o comentário
  vai pra revisão, a automação não dispara, e **o funil morre calado** — sem erro, sem
  aviso, sem nada aparecendo no painel.

### Exemplo de bio que funciona

```
One old recipe. Every morning. 🍯
```

Curta, primeira pessoa, sem promessa, com um emoji que **tem a ver com o produto**.
Emoji genérico (✨, 💪, 🔥) não diz nada e ainda tem cara de página automatizada.

---

## 🔴 Criar várias páginas sem levantar bandeira

O que derruba conta não é a quantidade de páginas — é o **padrão**.

Em ordem de risco:

1. **Criar em rajada.** Várias páginas no mesmo dia, mesmo aparelho, mesmo nicho. É o
   padrão que dispara revisão automática de *rede coordenada* — e aí o problema deixa de
   ser a página nova e passa a ser o perfil inteiro.
   ✅ **Uma página por dia, no máximo.**
2. **Conteúdo quase idêntico entre elas.** Mesma copy, mesma imagem, mesma keyword.
   ✅ Diferencie de propósito: **formato, cidade, persona, paleta e keyword**.
3. **Violação numa página.** Todas são administradas pelo mesmo perfil, então punição
   grave respinga. É por isso que a página de nicho mais sensível nasce separada e com
   compliance mais apertado.

**O que NÃO resolve:** criar perfis pessoais separados pra "isolar". Perfil falso é
violação direta dos termos, e a plataforma liga contas por aparelho, IP e navegador — o
resultado provável é perder tudo junto em vez de perder uma.

**Publicação:** ⛔ nunca duas páginas suas no mesmo horário. Elas não devem parecer ligadas.

---

## Rótulo de IA: ligar

Ligue o rótulo de conteúdo gerado por IA na publicação. Ele é campo da plataforma, custa
nada e protege a conta.

⛔ **Mas não ponha hashtag `#aigenerated` no texto.** O rótulo é metadado; a hashtag é
texto que o público lê, e é auto-sabotagem.

---

## ✅ Checklist antes de publicar a primeira vez

1. Bio preenchida, curta, sem link?
2. Website e link na bio vazios?
3. Filtro de palavrão **desligado**?
4. Cidade diferente das suas outras páginas?
5. Perfil coerente com o nome (pessoa→rosto, marca→logo)?
6. A capa promete algo que os vídeos ainda mostram?
7. Bridge do funil **no ar** (ver módulo 06)?
8. Automação de DM configurada **com a keyword desta página**?
9. Rótulo de IA ligado, hashtag de IA ausente?
