# Validação da cópia Windows

Verificação local em 12/11/2026, no checkout isolado preparado para este repositório:

- 45 testes da fila, recibos, composição/FFmpeg, atomicidade e configuração: passaram.
- 7 testes do supervisor de 30 minutos: passaram.
- 4 testes de admissão de imagens sincronizadas: passaram.
- 6 testes dos avisos do macro Windows: passaram.
- 70 arquivos Python analisados sintaticamente; nenhuma credencial encontrada
  nas verificações de tokens conhecidos, chaves privadas e atribuições sensíveis.

Os testes não acessam o Flow nem disparam gerações remotas. A cópia do supervisor
foi extraída da execução local e configurada para receber caminhos, projeto e
conta por um arquivo privado `config-lote.json`. Instalar em outra máquina exige
recriar o ambiente e autorizar o navegador, conforme `WINDOWS.md`.
