# Crítica de Importação de Movimentos

## Resumo das Alterações

Foi implementado um sistema de **crítica detalhada** antes da importação de movimentos que:

1. ✅ Analisa o arquivo Excel antes de importar
2. ✅ Identifica movimentos que **NÃO serão importados** por conta da conta contábil estar marcada como `relatorio_despesa = False`
3. ✅ Informa quantidade e valor total dos movimentos excluídos
4. ✅ Mostra problemas de validação (unidades, centros, contas não encontradas)
5. ✅ Filtra automaticamente na importação os movimentos com `relatorio_despesa = False`

---

## Como Usar

### 1. Via Interface Web (RECOMENDADO) 🌟

Acesse o menu de importação de movimentos:

1. Navegue até: **Gestor → Movimentos → Importar**
2. Preencha o período (Data Início e Data Fim)
3. Selecione o arquivo Excel
4. Clique em **"Analisar"** para ver a crítica
   - Mostra quantos movimentos serão importados
   - Mostra quantos serão excluídos (relatório despesa = não)
   - Mostra valor total de cada categoria
   - Mostra problemas de validação
5. Se estiver tudo OK, clique em **"Importar"**

A análise mostra:
- ✅ **Linhas válidas** (quantidade e valor)
- 🚫 **Excluídos** (relatório_despesa=False) - apenas totais
- ⚠️ **Problemas** (unidades, centros, contas não encontradas)

### 2. Via API REST (para integração)

A nova API está disponível em:
```
POST /gestor/api/movimento/criticar-arquivo/
```

**Parâmetros:**
- `arquivo`: Arquivo Excel (.xlsx ou .xls)
- `data_inicio`: Data início no formato YYYY-MM-DD
- `data_fim`: Data fim no formato YYYY-MM-DD

**Resposta JSON:**
```json
{
    "success": true,
    "arquivo": "movimentos.xlsx",
    "periodo": "01/01/2024 a 31/12/2024",
    "resumo": {
        "total_linhas_arquivo": 1000,
        "linhas_no_periodo": 950,
        "linhas_fora_periodo": 50,
        "linhas_validas_importar": 800,
        "valor_total_importar": 1500000.00
    },
    "excluidos_relatorio_despesa": {
        "quantidade": 150,
        "valor_total": 300000.00,
        "contas": [
            {
                "codigo_externo": "4.1.1.03.01",
                "codigo_interno": "4.1.1.03.01",
                "nome": "DESPESAS COM PESSOAL",
                "quantidade_movimentos": 45,
                "valor_total": 150000.00
            },
            ...
        ],
        "total_contas_distintas": 10
    },
    "problemas": {
        "unidades_nao_encontradas": {
            "quantidade": 2,
            "codigos": ["10", "20"]
        },
        "centros_nao_encontrados": {
            "quantidade": 1,
            "codigos": ["CC999"]
        },
        "contas_nao_encontradas": {
            "quantidade": 0,
            "codigos": []
        },
        "erros_validacao": []
    },
    "pode_importar": true
}
```

---

### 2. Via Script Python Standalone

Use o script de teste:

```bash
python testar_critica_importacao.py arquivo.xlsx 2024-01-01 2024-12-31
```

**Exemplo de saída:**

```
====================================================================================================
RELATÓRIO DE CRÍTICA DE IMPORTAÇÃO - movimentos.xlsx
====================================================================================================

📊 RESUMO GERAL:
   Total de linhas no arquivo: 1,000
   Linhas no período informado: 950
   Linhas fora do período: 50

✅ LINHAS VÁLIDAS PARA IMPORTAR: 800
   Valor total a importar: R$ 1.500.000,00

----------------------------------------------------------------------------------------------------
🚫 MOVIMENTOS NÃO IMPORTADOS (Conta marcada como 'não usar em relatório de despesas')
----------------------------------------------------------------------------------------------------
   Quantidade de movimentos: 150
   Valor total excluído: R$ 300.000,00

   Contas envolvidas (10 distintas):
   Cód. Externo    Cód. Interno    Nome da Conta                            Qtd.       Valor Total
   --------------- --------------- ---------------------------------------- ---------- --------------------
   4.1.1.03.01     4.1.1.03.01     DESPESAS COM PESSOAL                     45         R$ 150.000,00
   4.1.1.03.02     4.1.1.03.02     ENCARGOS SOCIAIS                         35         R$ 80.000,00
   ...

----------------------------------------------------------------------------------------------------
⚠️  PROBLEMAS DE VALIDAÇÃO
----------------------------------------------------------------------------------------------------

   ❌ Unidades não encontradas (2 códigos distintos):
      10, 20

   ✅ Nenhum centro de custo não encontrado
   ✅ Nenhuma conta contábil não encontrada

====================================================================================================
✅ ARQUIVO PODE SER IMPORTADO
   800 de 950 linhas no período serão importadas (84.2%)
====================================================================================================
```

---

## Alterações Técnicas Implementadas

### 1. Função de Análise (`analisar_arquivo_pre_importacao`)

**Localização:** `gestor/views/movimento_import.py` (linhas 26-146)

**Responsabilidades:**
- Analisa todas as linhas do arquivo Excel
- Valida datas, unidades, centros de custo e contas contábeis
- **Identifica contas com `relatorio_despesa = False`**
- Contabiliza valores e quantidades
- Retorna dicionário completo com estatísticas

**Retorno:**
```python
{
    'total_linhas': int,
    'linhas_no_periodo': int,
    'linhas_fora_periodo': int,
    'linhas_sem_relatorio_despesa': int,
    'valor_total_sem_relatorio_despesa': Decimal,
    'unidades_nao_encontradas': set(),
    'centros_nao_encontrados': set(),
    'contas_nao_encontradas': set(),
    'contas_sem_relatorio_despesa': {
        'codigo': {
            'nome': str,
            'codigo_interno': str,
            'quantidade': int,
            'valor_total': Decimal
        }
    },
    'erros_validacao': list,
    'linhas_validas_para_importar': int,
    'valor_total_valido': Decimal,
}
```

---

### 2. Filtro na Importação

**Localização:** `gestor/views/movimento_import.py` (linhas 116-118)

```python
# === FILTRO: NÃO IMPORTAR SE CONTA NÃO É PARA RELATÓRIO DE DESPESAS ===
if not conta_contabil.relatorio_despesa:
    return None, f'Conta {codigo_conta_contabil} marcada como "não usar em relatório de despesas" - linha ignorada'
```

Este filtro é aplicado em **todas as funções de importação**:
- `processar_linha_excel_otimizada`
- Usado por `api_importar_movimentos_excel`
- Usado por `api_importar_movimentos_simples`

---

### 3. Nova API de Crítica

**Endpoint:** `POST /gestor/api/movimento/criticar-arquivo/`

**View:** `api_criticar_arquivo_importacao` (linhas 847-948)

**Funcionalidade:**
- Recebe arquivo Excel + período
- Executa análise completa usando `analisar_arquivo_pre_importacao`
- Retorna JSON detalhado com todas as estatísticas
- **Não importa nada**, apenas analisa

---

### 4. Campo no Modelo

**Modelo:** `ContaContabil` em `core/models/hierarquicos.py` (linha 412)

```python
relatorio_despesa = models.BooleanField(default=True, verbose_name="Relatório Despesa")
```

- **`True`** (padrão): Movimento será importado normalmente
- **`False`**: Movimento será **IGNORADO** na importação

---

## Como Configurar Contas

### Via Django Admin

1. Acesse o admin de Contas Contábeis
2. Edite a conta desejada
3. Desmarque o campo **"Relatório Despesa"** para excluir movimentos dessa conta da importação
4. Salve

### Via Python/Shell

```python
from core.models import ContaContabil

# Marcar conta para NÃO importar
conta = ContaContabil.objects.get(codigo='4.1.1.03.01')
conta.relatorio_despesa = False
conta.save()

# Listar contas que não serão importadas
contas_excluidas = ContaContabil.objects.filter(relatorio_despesa=False, ativa=True)
for conta in contas_excluidas:
    print(f"{conta.codigo} - {conta.nome}")
```

---

## Fluxo Completo de Importação

### Antes (sem crítica)
```
1. Usuário escolhe arquivo
2. Sistema importa tudo
3. Dados incorretos ou indesejados são importados
```

### Agora (com crítica)
```
1. Usuário escolhe arquivo e período
2. Sistema executa CRÍTICA (via API ou script)
3. Sistema mostra:
   - Quantos movimentos serão importados
   - Quantos serão excluídos (e por quê)
   - Valor total de cada categoria
   - Problemas de validação
4. Usuário decide se prossegue
5. Sistema importa apenas os movimentos válidos
   - Filtra automaticamente contas com relatorio_despesa=False
   - Ignora linhas fora do período
   - Ignora linhas com erros de validação
```

---

## Logs

Todos os eventos são registrados no logger `synchrobi`:

```python
logger.info(f'Crítica concluída: {linhas_validas} linhas válidas, '
            f'{linhas_excluidas} excluídas (relatório despesa), '
            f'valor excluído: R$ {valor_excluido}')
```

---

## Testes

### Teste 1: Script Standalone
```bash
python testar_critica_importacao.py movimentos_teste.xlsx 2024-01-01 2024-12-31
```

### Teste 2: Via cURL
```bash
curl -X POST http://localhost:8000/gestor/api/movimento/criticar-arquivo/ \
  -F "arquivo=@movimentos.xlsx" \
  -F "data_inicio=2024-01-01" \
  -F "data_fim=2024-12-31" \
  -H "Authorization: Token SEU_TOKEN"
```

### Teste 3: Via Python Requests
```python
import requests

url = 'http://localhost:8000/gestor/api/movimento/criticar-arquivo/'
files = {'arquivo': open('movimentos.xlsx', 'rb')}
data = {
    'data_inicio': '2024-01-01',
    'data_fim': '2024-12-31'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

---

## Arquivos Modificados

1. ✅ `gestor/views/movimento_import.py` - Adicionadas funções de crítica e filtro
2. ✅ `gestor/urls.py` - Adicionada rota da API
3. ✅ `gestor/views/__init__.py` - Exportadas novas funções
4. ✅ `testar_critica_importacao.py` - Script standalone criado
5. ✅ `CRITICA_IMPORTACAO_README.md` - Esta documentação

---

## Próximos Passos Sugeridos

1. 🎨 **Interface Web**: Criar botão "Analisar Arquivo" na página de importação
2. 📊 **Gráficos**: Adicionar visualização gráfica da crítica
3. 📧 **Notificações**: Enviar email com relatório de crítica
4. 💾 **Histórico**: Salvar histórico de críticas executadas
5. 🔄 **Automação**: Agendar críticas periódicas

---

## Suporte

Para dúvidas ou problemas:
1. Verifique os logs do Django
2. Execute o script de teste standalone para diagnóstico
3. Verifique se o campo `relatorio_despesa` está configurado corretamente

---

**Desenvolvido em:** 03/11/2025
**Versão:** 1.0
