# Lote de receitas no Windows

Modelo extraído da automação de produção: 1.200 receitas, 600 `standard` e 600
`olive_honey_cinnamon`; quatro cenas de 8 segundos, final de 32 segundos.
Os estados, imagens e recibos reais não acompanham este código.

## Preparar uma execução

1. Instale o ambiente seguindo `WINDOWS.md` na raiz do repositório.
2. Dentro de `sistema-criativos-e-vsl`, copie esta pasta para
   `execucoes-noturnas/meu-lote`. Mantenha essa profundidade de pastas.
3. Copie `config-lote.example.json` para `config-lote.json` dentro da nova execução.
   Preencha entrada, saída, URL exata do projeto (inclusive `/u/N`) e conta esperada.
4. A entrada precisa de `manifesto.json` com uma lista `slots`: cada slot contém
   `id` numérico com padding, `slug` e `variant`. IDs de 001 a 1200; 600 de cada
   variante. As imagens ficam em `aprovadas/<id>_<slug>.png`.
5. Carregue `. .\env.ps1` e execute:

```powershell
python execucoes-noturnas\meu-lote\preparar-lote.py
python execucoes-noturnas\meu-lote\iniciar-sincronizacao.py
python execucoes-noturnas\meu-lote\iniciar-lote.py
```

A validação copia snapshots imutáveis, confere PNG/proporção/hashes e espera
arquivos ainda não sincronizados. O plano e os IDs não são recriados na retomada.
Abra o projeto correto no Chrome e permita a depuração remota solicitada pelo
navegador. O macro de produção usa mouse/teclado nativos e verifica zero créditos.

## Pilotos e continuação

O modelo inicia somente os três primeiros vídeos. Revise os pilotos; após a
revisão, crie `PILOTOS-APROVADOS.json` com `{"approved": true}` na execução.
Este marcador libera o restante da fila sem apagar o histórico.

```powershell
python execucoes-noturnas\meu-lote\iniciar-supervisor-30min.py
python execucoes-noturnas\meu-lote\status.py
```

Em bloqueio de atividade incomum ou falha transitória conhecida, o supervisor
espera **30 minutos**, atualiza as duas abas registradas do mesmo projeto,
reconcilia os recibos e retoma. Se o aviso continuar, espera mais 30 minutos.
Um clique incerto nunca é reenviado automaticamente. IDs recuperados são
baixados novamente sem gerar outro vídeo. A capacidade de um envio incerto
expirado pode ser liberada, mantendo o envio em quarentena para investigação.

Login, CAPTCHA, conta divergente, créditos/configuração divergentes e parada
explícita exigem revisão. `PARAR`, Esc e o canto superior esquerdo são respeitados.
O supervisor mantém o Windows acordado; não remove bloqueio de sessão.

## Auditoria e testes locais

```powershell
python execucoes-noturnas\meu-lote\auditar-entrega.py --concluidos
python execucoes-noturnas\meu-lote\test_supervisor_30min.py -v
python execucoes-noturnas\meu-lote\test_admissao_sync.py
```

No final, `auditar-entrega.py` sem flags exige todos os 1.200 vídeos e 4.800 cenas,
unicidade de hashes/IDs, continuidade dos frames, recibos e validação técnica.
Isso não substitui revisão visual humana. Nenhum teste local gera vídeos.
