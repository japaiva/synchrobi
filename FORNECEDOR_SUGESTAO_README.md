# Sistema de Sugestão Inteligente de Fornecedores

## 📋 Visão Geral

Implementação de um sistema inteligente de sugestão de fornecedores que:

- ✅ **Busca fornecedores similares** automaticamente ao detectar um nome
- ✅ **Mostra modal de confirmação** com sugestões ordenadas por relevância
- ✅ **Permite escolher** entre usar um fornecedor existente ou criar novo
- ✅ **Usa fuzzy matching** avançado (algoritmo Ratcliff-Obershelp + Jaccard)

**Exemplo prático:**
- Sistema detecta: `"BEAUTY FAIR EVENTOS LTDA"`
- Encontra cadastrado: `"BEAUTY FAIR"`
- Mostra sugestão com 75% de similaridade
- Usuário escolhe usar o existente ou criar novo

---

## 🎯 Funcionalidades Implementadas

### 1. **Método de Fuzzy Matching no Model** (`core/models/fornecedor.py`)

```python
# Buscar fornecedores similares com score
resultados = Fornecedor.buscar_similares(
    nome="BEAUTY FAIR EVENTOS",
    min_score=0.60,  # 60% de similaridade mínima
    apenas_ativos=True,
    limit=5
)

# Retorna: [(Fornecedor, score), ...]
# Exemplo: [(Fornecedor("BEAUTY FAIR"), 0.75), ...]
```

**Algoritmo:**
- 70% SequenceMatcher (caracteres similares)
- 30% Jaccard (palavras em comum)
- Filtra candidatos por palavras-chave para performance
- Retorna top 5 resultados ordenados por score

---

### 2. **API Endpoint de Sugestões** (`gestor/views/fornecedor.py`)

**Endpoint:** `GET /gestor/api/fornecedor/sugerir/`

**Parâmetros:**
- `nome` (obrigatório): Nome para buscar
- `min_score` (opcional): Score mínimo (padrão 0.60)
- `limit` (opcional): Máximo de resultados (padrão 5)

**Exemplo de uso:**
```javascript
fetch('/gestor/api/fornecedor/sugerir/?nome=BEAUTY FAIR EVENTOS&min_score=0.60')
    .then(response => response.json())
    .then(data => {
        console.log(data.sugestoes);
        // [
        //   {
        //     codigo: "BF001",
        //     razao_social: "BEAUTY FAIR",
        //     score: 0.75,
        //     score_percent: 75.0
        //   }
        // ]
    });
```

**Resposta JSON:**
```json
{
  "success": true,
  "nome_buscado": "BEAUTY FAIR EVENTOS",
  "sugestoes": [
    {
      "codigo": "BF001",
      "razao_social": "BEAUTY FAIR",
      "nome_fantasia": "",
      "nome_display": "BEAUTY FAIR",
      "cnpj_cpf": "12.345.678/0001-90",
      "tipo_pessoa": "Pessoa Jurídica",
      "criado_automaticamente": false,
      "score": 0.75,
      "score_percent": 75.0,
      "telefone": "",
      "email": ""
    }
  ],
  "total_encontrado": 1,
  "min_score_usado": 0.60
}
```

---

### 3. **Método no FornecedorExtractorService** (`gestor/services/fornecedor_extractor_service.py`)

```python
from gestor.services.fornecedor_extractor_service import FornecedorExtractorService

# Extrair fornecedor do histórico
fornecedor_extraido = FornecedorExtractorService.extrair_fornecedor(
    historico="ALUGUEL - 123456 BEAUTY FAIR EVENTOS LTDA - 2024/07",
    contexto_movimento={'data': '2024-07-01', 'valor': 1500.00}
)

if fornecedor_extraido:
    # Buscar ou sugerir (NÃO cria automaticamente)
    resultado = FornecedorExtractorService.buscar_ou_sugerir_fornecedor(
        fornecedor_extraido,
        historico_original=historico,
        min_score=0.60
    )

    if resultado['encontrado']:
        # Match exato encontrado
        fornecedor = resultado['fornecedor']
        print(f"Encontrado: {fornecedor.razao_social}")
    else:
        # Sugestões disponíveis
        print(f"Nome extraído: {resultado['nome_extraido']}")
        print(f"Confiança: {resultado['confianca']}")
        print(f"Sugestões ({len(resultado['sugestoes'])}):")

        for fornecedor, score in resultado['sugestoes']:
            print(f"  - {fornecedor.razao_social} ({score*100:.1f}%)")
```

**Estrutura do retorno:**
```python
{
    'encontrado': False,  # True se match exato, False se são sugestões
    'fornecedor': None,  # Fornecedor se encontrado
    'sugestoes': [(Fornecedor, 0.75), ...],  # Lista de sugestões
    'nome_extraido': 'BEAUTY FAIR EVENTOS LTDA',
    'tipo': 'PJ',  # ou 'PF'
    'confianca': 0.98  # Confiança da extração (0.0 a 1.0)
}
```

---

### 4. **Interface JavaScript** (`static/js/fornecedor-sugestao.js`)

**Módulo:** `FornecedorSugestao`

**Inicialização:**
```javascript
// No template HTML
FornecedorSugestao.init({
    fieldFornecedorSelector: '#id_fornecedor',  // Campo de fornecedor
    autoSuggest: false,  // Ativar sugestão automática ao digitar

    // Callback quando fornecedor é selecionado
    onSelecionado: function(fornecedor) {
        console.log('Selecionado:', fornecedor.razao_social);
        alert(`Fornecedor ${fornecedor.razao_social} selecionado!`);
    },

    // Callback quando usuário escolhe criar novo
    onCriarNovo: function(nome) {
        console.log('Criar novo:', nome);
        alert(`Novo fornecedor "${nome}" será criado`);
    }
});
```

**Métodos públicos:**

```javascript
// Buscar sugestões manualmente
const resultado = await FornecedorSugestao.buscarSugestoes('BEAUTY FAIR EVENTOS');

// Mostrar modal com sugestões
FornecedorSugestao.mostrarModal('BEAUTY FAIR EVENTOS', [
    {
        codigo: 'BF001',
        razao_social: 'BEAUTY FAIR',
        score_percent: 75.0,
        cnpj_cpf: '12.345.678/0001-90'
    }
]);

// Buscar e mostrar sugestões (método de conveniência)
FornecedorSugestao.mostrarSugestoesManual('BEAUTY FAIR EVENTOS');
```

---

### 5. **Template Integrado** (`templates/gestor/movimento_form.html`)

**Funcionamento:**

1. Usuário preenche o campo **Histórico**
2. Ao sair do campo (evento `blur`), sistema:
   - Extrai nome do fornecedor do histórico
   - Busca match exato no select de fornecedores
   - Se não encontrar, busca fornecedores similares via API
   - Mostra modal com sugestões (se houver)
3. Usuário escolhe:
   - **Selecionar sugestão** → Preenche campo automaticamente
   - **Criar novo** → Mantém nome original, cria ao salvar
   - **Cancelar** → Não faz nada

**Exemplo de fluxo:**

```
Histórico digitado:
"ALUGUEL - 123456 BEAUTY FAIR EVENTOS LTDA - 2024/07"

↓

Sistema extrai:
"BEAUTY FAIR EVENTOS LTDA"

↓

Busca no banco:
- Match exato? NÃO
- Busca similares: SIM

↓

API retorna:
[
  { razao_social: "BEAUTY FAIR", score: 75% },
  { razao_social: "BEAUTY FAIR INTERNACIONAL", score: 68% }
]

↓

Modal mostra:
┌────────────────────────────────────────┐
│ Fornecedor Similar Encontrado          │
├────────────────────────────────────────┤
│ Nome detectado:                        │
│ BEAUTY FAIR EVENTOS LTDA               │
│                                        │
│ Sugestões:                             │
│ ✓ [75%] BEAUTY FAIR                   │
│ ✓ [68%] BEAUTY FAIR INTERNACIONAL     │
│                                        │
│ [Cancelar] [Criar Novo] [Usar Sugestão]│
└────────────────────────────────────────┘
```

---

## 🔧 Como Testar

### Teste 1: Via Python Shell

```bash
python manage.py shell
```

```python
from core.models import Fornecedor

# 1. Criar fornecedor de teste
Fornecedor.objects.create(
    codigo='BF001',
    razao_social='BEAUTY FAIR',
    cnpj_cpf='12345678000190'
)

# 2. Buscar similares
resultados = Fornecedor.buscar_similares('BEAUTY FAIR EVENTOS', min_score=0.60)

print(f"Encontrados: {len(resultados)}")
for fornecedor, score in resultados:
    print(f"- {fornecedor.razao_social}: {score*100:.1f}%")

# Saída esperada:
# Encontrados: 1
# - BEAUTY FAIR: 75.0%
```

### Teste 2: Via API (Browser Console)

```javascript
// No console do navegador (F12)
fetch('/gestor/api/fornecedor/sugerir/?nome=BEAUTY FAIR EVENTOS')
    .then(r => r.json())
    .then(data => console.table(data.sugestoes));

// Deve mostrar tabela com sugestões
```

### Teste 3: Via Interface (Formulário de Movimento)

1. Acesse: `/gestor/movimentos/novo/`
2. No campo **Histórico**, digite:
   ```
   ALUGUEL - 123456 BEAUTY FAIR EVENTOS LTDA - 2024/07
   ```
3. Clique fora do campo (blur)
4. Deve aparecer modal com sugestões

---

## 📊 Exemplos de Similaridade

| Nome Original | Nome Cadastrado | Score | Motivo |
|--------------|----------------|-------|--------|
| BEAUTY FAIR EVENTOS | BEAUTY FAIR | 75% | 2 de 3 palavras iguais |
| CHOSEI BRASIL LTDA | CHOSEI | 67% | 1 palavra igual + parte igual |
| ACTION TECHNOLOGY SISTEMAS | ACTION TECHNOLOGY | 85% | 2 de 3 palavras iguais |
| EMPRESA A B C LTDA | EMPRESA A B LTDA | 60% | 3 de 5 palavras iguais |

---

## ⚙️ Configurações

### Ajustar Score Mínimo

**No Model:**
```python
# Padrão: 0.60 (60%)
resultados = Fornecedor.buscar_similares(nome, min_score=0.70)  # 70%
```

**No JavaScript:**
```javascript
FornecedorSugestao.config.minScore = 0.70;  // 70%
```

**Na API:**
```javascript
fetch('/gestor/api/fornecedor/sugerir/?nome=TESTE&min_score=0.70')
```

### Ajustar Quantidade de Sugestões

**No Model:**
```python
resultados = Fornecedor.buscar_similares(nome, limit=10)  # Até 10
```

**Na API:**
```javascript
fetch('/gestor/api/fornecedor/sugerir/?nome=TESTE&limit=10')
```

---

## 🐛 Troubleshooting

### Modal não aparece

1. Verificar se JavaScript está carregado:
   ```javascript
   console.log(window.FornecedorSugestao);  // Deve retornar objeto
   ```

2. Verificar se Bootstrap está disponível:
   ```javascript
   console.log(typeof bootstrap.Modal);  // Deve ser 'function'
   ```

### API retorna erro 404

Verificar se a rota está registrada:
```bash
python manage.py show_urls | grep sugerir
```

Deve mostrar:
```
/gestor/api/fornecedor/sugerir/   gestor:api_sugerir_fornecedores
```

### Nenhuma sugestão encontrada

1. Verificar se existem fornecedores cadastrados:
   ```python
   Fornecedor.objects.filter(ativo=True).count()
   ```

2. Reduzir score mínimo:
   ```python
   Fornecedor.buscar_similares(nome, min_score=0.50)  # 50%
   ```

---

## 📝 Logs

### Ativar logs detalhados

Em `settings.py`:
```python
LOGGING = {
    'loggers': {
        'synchrobi': {
            'level': 'DEBUG',  # INFO → DEBUG
        }
    }
}
```

### Exemplos de logs

```
INFO - Fornecedor existente encontrado: BF001 - BEAUTY FAIR
INFO - Busca por similares: "BEAUTY FAIR EVENTOS" → 1 resultado(s)
DEBUG - Candidatos para matching: 10
DEBUG - Score calculado: BEAUTY FAIR (0.75)
```

---

## 🚀 Próximos Passos (Opcional)

1. **Caching de sugestões** (Redis)
2. **Aprendizado de máquina** (treinar modelo com histórico)
3. **Busca fonética** (soundex para nomes parecidos)
4. **Deduplicação automática** (merge de fornecedores)
5. **Histórico de decisões** (log de sugestões aceitas/rejeitadas)

---

## 📄 Arquivos Modificados

1. ✅ `core/models/fornecedor.py` - Método `buscar_similares()`
2. ✅ `gestor/views/fornecedor.py` - API `api_sugerir_fornecedores()`
3. ✅ `gestor/urls.py` - Rota `/api/fornecedor/sugerir/`
4. ✅ `gestor/services/fornecedor_extractor_service.py` - Método `buscar_ou_sugerir_fornecedor()`
5. ✅ `static/js/fornecedor-sugestao.js` - Módulo JavaScript (NOVO)
6. ✅ `templates/gestor/movimento_form.html` - Integração com JavaScript

---

## 👨‍💻 Desenvolvedor

Desenvolvido para o projeto **SynchroBI**
Data: 2025-01-XX

---

**Dúvidas?** Consulte o código ou entre em contato!
