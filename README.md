# CFG · Estudo e Simulados

App de estudo para a certificação **CFG (ANBIMA)**: apostila de cada tema e
simulados com correção comentada. Funciona no celular, pode ser instalado na
tela inicial e abre sem internet depois do primeiro acesso.

**Abrir:** https://mmansurbr-code.github.io/simulados-cfg/

## O que tem

| Tema | Peso na prova | Apostila | Questões |
|---|---|---|---|
| 1 · Métodos Quantitativos | 8–12% | 5 tópicos | 62 |
| 2 · Economia | 3–7% | 2 tópicos | 91 |
| 3 · Análise de Relatórios Financeiros | 3–7% | 3 tópicos | 56 |
| 4 · Finanças Corporativas | 3–7% | 5 tópicos | 80 |
| 5 · Mercados e Instrumentos Financeiros | 13–17% | 7 tópicos | 41 |
| 6 · Teoria Moderna de Carteiras e Precificação de Ativos | 8–12% | 8 tópicos | 78 |
| 7 · Finanças Comportamentais | 3–7% | 4 tópicos | 53 |
| 8 · Política de Investimento (IPS) | 3–7% | 3 tópicos | 54 |
| 9 · Alocação de Ativos | 13–17% | 3 tópicos | 33 |
| 10 · Novas Tecnologias em Finanças | 3–7% | 4 tópicos | 54 |
| 11 · Ética e Autorregulação | 8–12% | 4 tópicos | 63 |
| 12 · Legislação e Regulação | 8–12% | 4 tópicos | 93 |
| Revisão geral | — | — | 10 |

Os 12 temas do programa estão cobertos: 768 questões comentadas.

- **Estudar:** lê cada tópico, marca como lido e pratica só aquele subtema.
- **Praticar:** treino (corrige a cada questão) ou simulado (3 min por questão,
  aprovação com 70%), filtrando por tema e por questões novas ou erradas.
- **Ouvir:** cada subtema tem uma faixa de conteúdo e uma de perguntas (com
  pausa para pensar antes da resposta), 17 horas no total. O tocador segue
  sozinho para a próxima faixa e aceita os botões do carro e do fone; "Baixar
  para o carro" guarda os áudios de um tema no celular para tocar sem internet.
- **Progresso:** fica no aparelho. Em *Mais* dá para salvar um arquivo e
  carregar em outro aparelho.

## Apostilas

Tudo fica em `apostilas/`:

```
apostilas/html/        fonte de cada tema (apostila + simulado interativo)
apostilas/impressao/   versão para imprimir (.docx e .pdf): apostila, simulado e gabarito comentado
apostilas/kindle/      EPUBs
apostilas/audio/       áudios (MP3 por tema) e roteiros/ com o texto falado
```

## Como atualizar o conteúdo

Depois de pôr ou alterar uma apostila em `apostilas/html/`:

```bash
python ferramentas/importar.py
python ferramentas/imprimir.py "apostilas/html/CFG Tema N - ... .html"
```

Para os áudios (precisa de internet; `pip install edge-tts imageio-ffmpeg`):

```bash
python ferramentas/audio.py 6      # um tema; sem número, todos
```

O `importar.py` regenera `dados/` e atualiza em `sw.js` a lista de arquivos
offline e a `VERSAO`. O `imprimir.py` usa o Word (Windows) para gerar o .docx e
o .pdf. Questões avulsas (sem apostila) vão em `dados/manuais/`.

## Estrutura

```
index.html  estilo.css  app.js      app (sem build, sem dependências)
sw.js  manifest.webmanifest         offline e instalação
dados/                              temas e questões (gerados)
apostilas/                          fontes, impressão, Kindle e áudio
ferramentas/importar.py             apostilas HTML/EPUB -> dados/
ferramentas/imprimir.py             apostila HTML -> .docx/.pdf para imprimir
ferramentas/gerar_epub.py           apostilas HTML -> EPUB (Kindle)
ferramentas/audio.py                roteiros e questões -> MP3 + dados/audios.json
ferramentas/icones.py               gera os ícones PNG
```

Material de estudo próprio, baseado no programa da certificação. Não é
material oficial da ANBIMA.
