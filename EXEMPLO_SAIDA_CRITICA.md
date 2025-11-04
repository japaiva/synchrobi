# Exemplo de Saída da Crítica de Importação

## Formato Atual (com detalhamento linha por linha)

### Via Interface Web

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Análise do Arquivo: movimentos_janeiro_2024.xlsx                           │
│ Período: 01/01/2024 a 31/01/2024                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 📊 RESUMO GERAL                                                             │
│                                                                             │
│   Total Linhas: 1,000          No Período: 950                             │
│   ✅ Serão Importadas: 750     R$ 1.800.000,00                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 🚫 Movimentos NÃO Importados - Detalhamento                                │
│                                                                             │
│ ┌────────────────────────┬─────────────────────────┬──────┬────────────┐  │
│ │ Motivo                 │ Detalhe                 │ Qtd. │ Valor      │  │
│ ├────────────────────────┼─────────────────────────┼──────┼────────────┤  │
│ │ Conta sem Relatório    │ 3.1.1.01.01 - SALÁRIOS  │  45  │ R$ 90.000  │  │
│ │ Conta sem Relatório    │ 3.1.1.02.01 - ENCARGOS  │  35  │ R$ 70.000  │  │
│ │ Unidade não encontrada │ Código: 999             │  50  │ R$ 25.000  │  │
│ │ Centro não encontrado  │ Código: CC-NOVO         │  30  │ R$ 15.000  │  │
│ │ Conta não encontrada   │ Código: 9.9.9.99        │  40  │ R$ 10.000  │  │
│ ├────────────────────────┴─────────────────────────┼──────┼────────────┤  │
│ │ TOTAL GERAL                                      │  200 │ R$ 210.000 │  │
│ └──────────────────────────────────────────────────┴──────┴────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ✅ ARQUIVO PODE SER IMPORTADO                                              │
│ Clique em "Importar" para prosseguir                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Via Script Python

```
================================================================================
RELATÓRIO DE CRÍTICA DE IMPORTAÇÃO - movimentos_janeiro_2024.xlsx
================================================================================

📊 RESUMO GERAL:
   Total de linhas no arquivo: 1,000
   Linhas no período informado: 950
   Linhas fora do período: 50

✅ MOVIMENTOS VÁLIDOS (serão importados): 750
   Valor total a importar: R$ 1.800.000,00

🚫 MOVIMENTOS NÃO IMPORTADOS: 200
   Valor total não importado: R$ 210.000,00

--------------------------------------------------------------------------------
🚫 MOVIMENTOS NÃO IMPORTADOS - DETALHAMENTO
--------------------------------------------------------------------------------

   Motivo                         Detalhe                                                           Qtd.    Valor Total
   ------------------------------ ----------------------------------------------------------------- -------- --------------------
   Conta sem Relatório Despesa    3.1.1.01.01 - SALÁRIOS E ORDENADOS                                    45       R$ 90.000,00
   Conta sem Relatório Despesa    3.1.1.02.01 - ENCARGOS SOCIAIS                                        35       R$ 70.000,00
   Unidade não encontrada         Código: 999                                                           50       R$ 25.000,00
   Centro não encontrado          Código: CC-NOVO                                                       30       R$ 15.000,00
   Conta não encontrada           Código: 9.9.9.99                                                      40       R$ 10.000,00
   ------------------------------ ----------------------------------------------------------------- -------- --------------------
   TOTAL GERAL                                                                                          200      R$ 210.000,00

================================================================================
✅ ARQUIVO PODE SER IMPORTADO

   Resumo:
   - Total no período: 950 movimentos
   - ✅ Serão importados: 750 (78.9%) - R$ 1.800.000,00
   - 🚫 Não serão importados: 200 (21.1%) - R$ 210.000,00
================================================================================
```

## Estrutura da Resposta JSON

```json
{
  "success": true,
  "arquivo": "movimentos_janeiro_2024.xlsx",
  "periodo": "01/01/2024 a 31/01/2024",
  "resumo": {
    "total_linhas_arquivo": 1000,
    "linhas_no_periodo": 950,
    "linhas_fora_periodo": 50,
    "linhas_validas_importar": 750,
    "valor_total_importar": 1800000.00
  },
  "movimentos_nao_importados": {
    "total_quantidade": 200,
    "total_valor": 210000.00,
    "total_linhas": 5,
    "linhas": [
      {
        "motivo": "Conta sem Relatório Despesa",
        "detalhe": "3.1.1.01.01 - SALÁRIOS E ORDENADOS",
        "codigo": "3.1.1.01.01",
        "nome": "SALÁRIOS E ORDENADOS",
        "quantidade": 45,
        "valor_total": 90000.00
      },
      {
        "motivo": "Conta sem Relatório Despesa",
        "detalhe": "3.1.1.02.01 - ENCARGOS SOCIAIS",
        "codigo": "3.1.1.02.01",
        "nome": "ENCARGOS SOCIAIS",
        "quantidade": 35,
        "valor_total": 70000.00
      },
      {
        "motivo": "Unidade não encontrada",
        "detalhe": "Código: 999",
        "codigo": "999",
        "nome": "",
        "quantidade": 50,
        "valor_total": 25000.00
      },
      {
        "motivo": "Centro de Custo não encontrado",
        "detalhe": "Código: CC-NOVO",
        "codigo": "CC-NOVO",
        "nome": "",
        "quantidade": 30,
        "valor_total": 15000.00
      },
      {
        "motivo": "Conta Contábil não encontrada",
        "detalhe": "Código: 9.9.9.99",
        "codigo": "9.9.9.99",
        "nome": "",
        "quantidade": 40,
        "valor_total": 10000.00
      }
    ]
  },
  "pode_importar": true
}
```

## Características

### ✅ O que mostra:

1. **Resumo Geral:**
   - Total de linhas no arquivo
   - Linhas no período
   - Linhas que serão importadas (quantidade + valor)
   - Linhas que NÃO serão importadas (quantidade + valor)

2. **Detalhamento dos Não Importados (TABELA):**
   - **1 linha por erro/motivo**
   - Cada linha mostra:
     - Motivo (tipo de erro)
     - Detalhe (código + nome quando aplicável)
     - Quantidade de movimentos afetados
     - Valor total

3. **Tipos de erro mostrados:**
   - Conta sem Relatório Despesa (`relatorio_despesa = False`)
   - Unidade não encontrada
   - Centro de Custo não encontrado
   - Conta Contábil não encontrada

4. **Total Geral:**
   - Linha final com soma de todos os movimentos não importados
   - Quantidade total + Valor total

### 📊 Ordenação:

- Linhas ordenadas por **valor total** (maior primeiro)
- Facilita identificar os erros mais impactantes

### 🎯 Benefícios:

- **Clareza:** Uma linha por erro facilita a leitura
- **Ação:** Fácil identificar o que precisa ser corrigido
- **Priorização:** Valores maiores aparecem primeiro
- **Completude:** Mostra TODOS os erros, não apenas resumo
- **Rastreabilidade:** Cada erro com seu impacto (quantidade + valor)
