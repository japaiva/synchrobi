# Formato Final da Crítica de Importação

## Estrutura da Saída

### 1. ✅ Movimentos Válidos (serão importados)
- Quantidade
- Valor Total

### 2. 🚫 Movimentos NÃO Importados

#### 2.1. TOTAL NÃO É RELATÓRIO DE DESPESA ⚠️
**Apenas totais (não lista detalhes)**
- Quantidade
- Valor Total

#### 2.2. ERROS DE VALIDAÇÃO 📋
**Tabela detalhada linha por linha**
- Unidade não encontrada (código + qtd + valor)
- Centro não encontrado (código + qtd + valor)
- Conta não encontrada (código + qtd + valor)
- **Subtotal Erros** (soma dos erros)

#### 2.3. TOTAL GERAL NÃO IMPORTADOS
- Soma de tudo (relatório despesa + erros)

---

## Exemplo de Saída - Interface Web

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 RESUMO GERAL                                             │
├─────────────────────────────────────────────────────────────┤
│ Total Linhas: 1,000                                         │
│ No Período: 950                                             │
│ ✅ Serão Importadas: 700 - R$ 1.500.000,00                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🚫 MOVIMENTOS NÃO IMPORTADOS                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ⚠️  TOTAL NÃO É RELATÓRIO DE DESPESA:                      │
│     Quantidade: 150 movimentos                              │
│     Valor Total: R$ 250.000,00                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 📋 DETALHAMENTO DE ERROS DE VALIDAÇÃO:                      │
│                                                             │
│ ┌────────────────────┬────────────────┬─────┬──────────┐   │
│ │ Motivo             │ Detalhe        │ Qtd │ Valor    │   │
│ ├────────────────────┼────────────────┼─────┼──────────┤   │
│ │ Unidade não        │ Código: 999    │  50 │ R$ 80k   │   │
│ │ Centro não         │ Código: CC-999 │  30 │ R$ 60k   │   │
│ │ Conta não          │ Código: 9.9.9  │  20 │ R$ 40k   │   │
│ ├────────────────────┴────────────────┼─────┼──────────┤   │
│ │ Subtotal Erros                      │ 100 │ R$ 180k  │   │
│ └─────────────────────────────────────┴─────┴──────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 🔴 TOTAL GERAL NÃO IMPORTADOS:                              │
│    Quantidade: 250 movimentos                               │
│    Valor Total: R$ 430.000,00                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Exemplo de Saída - Script Python

```
==============================================================================
RELATÓRIO DE CRÍTICA DE IMPORTAÇÃO - movimentos.xlsx
==============================================================================

📊 RESUMO GERAL:
   Total de linhas no arquivo: 1,000
   Linhas no período informado: 950
   Linhas fora do período: 50

✅ MOVIMENTOS VÁLIDOS (serão importados): 700
   Valor total a importar: R$ 1.500.000,00

🚫 MOVIMENTOS NÃO IMPORTADOS: 250
   Valor total não importado: R$ 430.000,00

------------------------------------------------------------------------------
🚫 MOVIMENTOS NÃO IMPORTADOS
------------------------------------------------------------------------------

   ⚠️  TOTAL NÃO É RELATÓRIO DE DESPESA:
       Quantidade:      150 movimentos
       Valor Total:        R$ 250.000,00

   📋 DETALHAMENTO DE ERROS DE VALIDAÇÃO:

   Motivo                         Detalhe                      Qtd.        Valor
   ------------------------------ ---------------------------- -------- --------------------
   Unidade não encontrada         Código: 999                        50       R$ 80.000,00
   Centro não encontrado          Código: CC-999                     30       R$ 60.000,00
   Conta não encontrada           Código: 9.9.9                      20       R$ 40.000,00
   ------------------------------ ---------------------------- -------- --------------------
   Subtotal Erros                                                    100      R$ 180.000,00

   ==========================================================================================
   TOTAL GERAL NÃO IMPORTADOS                                        250      R$ 430.000,00
   ==========================================================================================

==============================================================================
✅ ARQUIVO PODE SER IMPORTADO

   Resumo:
   - Total no período: 950 movimentos
   - ✅ Serão importados: 700 (73.7%) - R$ 1.500.000,00
   - 🚫 Não serão importados: 250 (26.3%) - R$ 430.000,00
==============================================================================
```

---

## Resposta JSON da API

```json
{
  "success": true,
  "arquivo": "movimentos.xlsx",
  "periodo": "01/01/2024 a 31/12/2024",

  "resumo": {
    "total_linhas_arquivo": 1000,
    "linhas_no_periodo": 950,
    "linhas_fora_periodo": 50,
    "linhas_validas_importar": 700,
    "valor_total_importar": 1500000.00
  },

  "sem_relatorio_despesa": {
    "quantidade": 150,
    "valor_total": 250000.00
  },

  "erros_validacao": {
    "total_quantidade": 100,
    "total_valor": 180000.00,
    "total_tipos": 3,
    "linhas": [
      {
        "motivo": "Unidade não encontrada",
        "detalhe": "Código: 999",
        "codigo": "999",
        "nome": "",
        "quantidade": 50,
        "valor_total": 80000.00
      },
      {
        "motivo": "Centro de Custo não encontrado",
        "detalhe": "Código: CC-999",
        "codigo": "CC-999",
        "nome": "",
        "quantidade": 30,
        "valor_total": 60000.00
      },
      {
        "motivo": "Conta Contábil não encontrada",
        "detalhe": "Código: 9.9.9",
        "codigo": "9.9.9",
        "nome": "",
        "quantidade": 20,
        "valor_total": 40000.00
      }
    ]
  },

  "total_nao_importados": {
    "quantidade": 250,
    "valor": 430000.00
  },

  "pode_importar": true
}
```

---

## Características

### ✅ Vantagens:

1. **Relatório Despesa separado**
   - Não polui a tabela de erros
   - Mostra apenas total (qtd + valor)
   - Destaque visual (box amarelo)

2. **Erros de validação detalhados**
   - Tabela limpa e organizada
   - 1 linha por código com problema
   - Quantidade e valor por erro
   - Subtotal dos erros

3. **Total Geral claro**
   - Soma de tudo (relatório + erros)
   - Destaque visual (box vermelho)

4. **Fácil leitura**
   - Hierarquia visual clara
   - Cores diferenciadas por tipo
   - Valores alinhados à direita

### 🎯 Como interpretar:

**Total Geral = Relatório Despesa + Erros de Validação**

Exemplo:
- Sem Relatório Despesa: 150 movimentos (R$ 250k)
- Erros de Validação: 100 movimentos (R$ 180k)
- **TOTAL:** 250 movimentos (R$ 430k)

### 📋 Ações sugeridas:

1. **Relatório Despesa = Não**
   - Verificar se as contas estão marcadas corretamente
   - Ajustar campo `relatorio_despesa` se necessário

2. **Erros de Validação**
   - Cadastrar códigos faltantes
   - Corrigir arquivo Excel se códigos estão errados
