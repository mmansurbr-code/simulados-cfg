# CFG · Estudo e Simulados

App de estudo para a certificação **CFG (ANBIMA)**: apostila de cada tema e
simulados com correção comentada. Funciona no celular, pode ser instalado na
tela inicial e abre sem internet depois do primeiro acesso.

**Abrir:** https://mmansurbr-code.github.io/simulados-cfg/

## O que tem

| Tema | Apostila | Questões |
|---|---|---|
| 5 · Mercados e Instrumentos Financeiros | 7 tópicos | 41 |
| 9 · Alocação de Ativos | 3 tópicos | 33 |
| Revisão geral (outros temas) | — | 10 |

- **Estudar:** lê cada tópico, marca como lido e pratica só aquele subtema.
- **Praticar:** treino (corrige a cada questão) ou simulado (3 min por questão,
  aprovação com 70%), filtrando por tema e por questões novas ou erradas.
- **Progresso:** fica no aparelho. Em *Mais* dá para salvar um arquivo e
  carregar em outro aparelho.

## Como atualizar o conteúdo

As apostilas de origem ficam na pasta `CFG` (um nível acima deste repositório):
`CFG Tema N - ... .html` e o EPUB da pasta `Kindle`.

```bash
python ferramentas/importar.py ..
```

Isso regenera `dados/`. Para um tema novo, acrescente também o arquivo
`dados/temaN.json` à lista `ARQUIVOS` e troque a `VERSAO` em `sw.js`.
Questões avulsas (sem apostila) vão em `dados/manuais/`.

## Estrutura

```
index.html  estilo.css  app.js      app (sem build, sem dependências)
sw.js  manifest.webmanifest         offline e instalação
dados/                              temas e questões (gerados)
ferramentas/importar.py             apostilas HTML/EPUB -> dados/
ferramentas/icones.py               gera os ícones PNG
```

Material de estudo próprio, baseado no programa da certificação. Não é
material oficial da ANBIMA.
