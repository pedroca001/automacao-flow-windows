# Flow no Windows

Instalação nesta máquina: `C:\Users\Pedro\Desktop\flow`.
O código original para macOS foi preservado. Os resultados e caminhos de produção
do Mac nos documentos antigos são históricos; as mídias não estão no GitHub.

## Uso por duplo clique

Os atalhos estão nesta pasta e em `sistema-criativos-e-vsl/`:

1. **Preparar Flow Noturno.cmd**: selecione a pasta de imagens e cole o link do
   projeto. Nomes: `PAR-001_hook.png` e `PAR-001_recipe.png`. Só prepara o plano.
2. **Flow Noturno.cmd**: inicia a fila preparada em segundo plano. Pode fechar
   esta janela e o Codex. Mantenha o computador ligado e a sessão desbloqueada.
3. **Relatorio Flow Noturno.cmd**: atualiza o relatório. Vídeos ficam em
   `sistema-criativos-e-vsl/execucoes-noturnas/<execução>/Montados para revisar/`.
4. **Parar Flow Noturno.cmd**: solicita parada e preserva os recibos.

**Macro Flow.cmd** abre a janela para uma cena, com botões Configurar,
Preparar sem enviar e Gerar uma vez. **Verificar Windows.cmd** confere os
programas e modelos locais, sem abrir o Flow.

## Chrome: configuração inicial

Abra o Chrome normal, entre na sua conta e abra o projeto em
`https://flow.google.com/`. Deixe esse projeto na aba ativa da janela.

Para a fila consultar o andamento e baixar os arquivos, abra
`chrome://inspect/#remote-debugging`, habilite **Allow remote debugging for this
browser instance** e aceite **Allow/Permitir** quando o Chrome solicitar.
Essa configuração pertence ao navegador e precisa ser feita na máquina Windows.
Nenhum login, token ou cookie do Mac é importado.

O macro localiza os controles pela acessibilidade do Windows e usa mouse e
teclado reais. Se não encontrar o conteúdo do projeto, abra
`chrome://accessibility/` e habilite **Native accessibility API support**.
Uma alternativa é iniciar o Chrome com `--force-renderer-accessibility`.

Não use o mouse ou teclado durante o macro. Esc e o canto superior esquerdo
interrompem a operação. O sistema confere Vídeo / Elementos / Veo 3.1 Lite
Lower Priority / 9:16 / 8s / x1 / **0 créditos**, e interrompe se a configuração
divergir. Login, CAPTCHA e mudanças na interface exigem intervenção na página.

## Terminal PowerShell

```powershell
cd C:\Users\Pedro\Desktop\flow\sistema-criativos-e-vsl
. .\env.ps1
python retomada-macro\noturno.py preparar --imagens 'C:\minhas imagens' --projeto 'URL_OU_UUID'
python retomada-macro\noturno.py executar --validar
python retomada-macro\noturno.py iniciar
python retomada-macro\noturno.py relatorio
python retomada-macro\noturno.py parar
```

Se a política local impedir carregar `env.ps1`, use os atalhos `.cmd` ou abra
`cmd.exe` e execute `call env.cmd`. Não é necessário alterar a política global.
Para uma cena: `flow-macro.cmd --arquivo prompt.txt --preparar --projeto UUID`.
Para os scripts do fornecedor: `criativos-run.cmd gerar_specs.py scripts\exemplo-leva.json`.
`criativos-run.cmd driver` e `download` executam os scripts dentro do browser-harness.
As variáveis do pipeline continuam disponíveis; no PowerShell use `$env:LEVA = 'C:\pasta'`.

## Reinstalação

Execute **Instalar Windows.cmd**. Requer Python 3.11 via uv, FFmpeg com libass
no PATH e Chrome. O instalador cria `.venv`, instala Pillow, edge-tts, psutil,
pywinauto e browser-harness quando ausente, copia as sete skills e baixa o
Whisper oficial para Windows e o modelo small (aproximadamente 466 MB).
Ferramentas e modelos ficam locais e fora do Git.

Para instalar também a remoção de fundo RVM, incluindo Torch para CPU:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\Instalar Windows.ps1' -Rvm
```

RVM escolhe CUDA quando disponível; a instalação padrão acima usa Torch CPU.
O pip freeze antigo `requirements-instalado.txt` registra o Mac e não é a lista
de instalação do Windows. Aqui usamos `requirements-windows.txt`.

## Validação sem gerar

Conferência local em 21/10/2026: **37 testes passaram** (28 da fila e 9 do
Windows), incluindo transcrição com Whisper small e exportação com o RVM.
Whisper, modelo small, Torch CPU, torchvision e os pesos RVM estão instalados
nesta máquina. As gerações no Flow ainda dependem da permissão no Chrome e do
projeto aberto; nenhuma geração foi executada durante a instalação.

```powershell
. .\sistema-criativos-e-vsl\env.ps1
python sistema-criativos-e-vsl\scripts\windows_launcher.py verificar
python -m unittest discover -s sistema-criativos-e-vsl\retomada-macro -p 'test_noturno*.py' -v
python -m unittest discover -s sistema-criativos-e-vsl\scripts -p 'test_windows.py' -v
python sistema-criativos-e-vsl\scripts\windows_launcher.py conexao
```

Os testes verificam a fila, downloads, montagem de 40s, travas entre processos,
execução independente da janela e legendas com caminhos Windows. A conexão
consulta apenas a quantidade de abas do Flow. A validação online completa de
geração só pode ser feita com uma nova leva solicitada pelo usuário.
