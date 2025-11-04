# Solução para Erro: "não usar em relatório de despesas"

## 🔴 Problema

Durante a importação de movimentos, você está recebendo erros como:

```
Conta 6101010003 marcada como "não usar em relatório de despesas" - linha ignorada
```

Isso acontece porque algumas contas contábeis estão com o campo `relatorio_despesa = False`, que foi implementado para filtrar automaticamente quais movimentos devem ser importados.

## 📊 Entendendo o Campo

**`relatorio_despesa`** (na tabela `contas_contabeis`):
- **`True`**: Movimentos dessa conta SERÃO importados ✅
- **`False`**: Movimentos dessa conta NÃO SERÃO importados 🚫

Este filtro foi criado a pedido para excluir automaticamente certas contas da importação.

## 🛠️ Soluções

### **Solução 1: Script Standalone (MAIS FÁCIL)**

Execute o script automático:

```bash
cd /Users/joseantoniopaiva/pythonprojects/ikesaki && source .venv/bin/activate && cd synchrobi
python corrigir_relatorio_despesa_standalone.py
```

O script irá:
1. ✅ Mostrar quantas contas estão com problema
2. ✅ Listar as contas afetadas
3. ✅ Oferecer opção para atualizar TODAS de uma vez
4. ✅ Usar transação (tudo ou nada)

**Exemplo de saída:**
```
===============================================================================
DIAGNÓSTICO E CORREÇÃO - RELATÓRIO DE DESPESA
===============================================================================

📊 SITUAÇÃO ATUAL:
   Contas com relatorio_despesa = False: 45
   Códigos externos (ERP) afetados: 127

📋 CONTAS COM PROBLEMA:
   Código               Nome
   -------------------- ---------------------------------------------------------------
   010.010.01           Revenda de Mercadoria
   130.010.01.01        Salários e Ordenados
   ...

OPÇÕES:
1. Atualizar TODAS para relatorio_despesa = True (recomendado)
2. Mostrar códigos externos bloqueados
0. Sair

Escolha uma opção: 1

🔴 Confirma? (digite SIM): SIM

✅ SUCESSO!
   45 contas atualizadas
   Agora você pode importar os movimentos novamente
```

---

### **Solução 2: Via Django Shell (MAIS FLEXÍVEL)**

```bash
python manage.py shell < verificar_contas_relatorio_despesa.py
```

**Funções disponíveis:**

1. **Listar contas com problema:**
```python
>>> listar_contas_sem_relatorio()
```

2. **Ver um código específico:**
```python
>>> listar_contas_codigo_especifico('6101010003')
```

3. **Buscar todos os códigos bloqueados:**
```python
>>> buscar_codigos_externos_problematicos()
```

4. **Atualizar TODAS as contas:**
```python
>>> atualizar_todas_para_sim(confirmar=True)
```

5. **Atualizar contas específicas:**
```python
>>> atualizar_contas_especificas(['010.010.01', '130.010.01.01'], confirmar=True)
```

---

### **Solução 3: SQL Direto (RÁPIDO)**

Se preferir usar SQL direto:

```sql
-- Ver quantas contas têm problema
SELECT COUNT(*) FROM contas_contabeis WHERE relatorio_despesa = 0;

-- Listar as contas
SELECT codigo, nome FROM contas_contabeis WHERE relatorio_despesa = 0;

-- ATUALIZAR TODAS (CUIDADO!)
UPDATE contas_contabeis SET relatorio_despesa = 1;

-- Ou atualizar contas específicas
UPDATE contas_contabeis
SET relatorio_despesa = 1
WHERE codigo IN ('010.010.01', '130.010.01.01');
```

---

## 🎯 Recomendação

**Use a Solução 1** (script standalone):
- ✅ Mais seguro (pede confirmação)
- ✅ Mostra diagnóstico completo
- ✅ Usa transação do Django
- ✅ Não precisa saber SQL

---

## 🔍 Como Identificar o Problema Antes de Importar

Use o botão **"Analisar"** na tela de importação de movimentos:

1. Gestor → Movimentos → Importar
2. Selecione arquivo e período
3. Clique em **"Analisar"**
4. Veja a seção "Total NÃO é Relatório de Despesa"

Isso mostra ANTES de importar:
- Quantos movimentos serão bloqueados
- Valor total bloqueado
- Evita erros durante importação

---

## ⚙️ Configuração Manual (Caso a Caso)

Se você quiser manter algumas contas bloqueadas e liberar apenas algumas:

1. Acesse: Django Admin → Contas Contábeis
2. Encontre a conta desejada
3. Edite a conta
4. Marque/desmarque **"Relatório Despesa"**
5. Salve

**OU**

Use a função de atualização específica:
```python
atualizar_contas_especificas(['codigo1', 'codigo2'], confirmar=True)
```

---

## 📝 Histórico do Campo

Este campo foi criado para:
- Filtrar automaticamente contas que não devem aparecer em relatórios de despesas
- Exemplo: contas de receita, patrimônio, etc.

Se TODAS as suas contas devem ser importadas, execute a **Solução 1** e atualize tudo para `True`.

Se apenas ALGUMAS contas devem ser bloqueadas, use a interface do Django Admin para configurar manualmente.

---

## 🆘 Precisa de Ajuda?

1. Execute o diagnóstico:
   ```bash
   python corrigir_relatorio_despesa_standalone.py
   ```

2. Veja quais contas estão bloqueadas

3. Decida se quer:
   - Liberar TODAS (mais comum)
   - Liberar ALGUMAS (mais controle)
   - Manter bloqueadas (se realmente não deve importar)

4. Execute a correção apropriada
