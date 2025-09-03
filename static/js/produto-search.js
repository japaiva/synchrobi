// static/js/produto-search.js
// Busca simples de produtos para pedidos de compra

class ProdutoSearch {
    constructor(input) {
        this.input = input;
        this.produtoHiddenInput = null;
        this.dropdown = null;
        this.timeout = null;
        this.produtos = [];
        
        this.init();
    }
    
    init() {
        // Encontrar o campo hidden do produto
        this.findProdutoHiddenInput();
        
        // Criar dropdown de resultados
        this.createDropdown();
        
        // Adicionar event listeners
        this.attachEvents();
    }
    
    findProdutoHiddenInput() {
        // Buscar campo hidden na mesma linha da tabela
        const row = this.input.closest('tr');
        if (row) {
            // 🔧 CORREÇÃO: Pegar APENAS O PRIMEIRO campo hidden com produto
            const hiddenInputs = row.querySelectorAll('input[name*="-produto"][type="hidden"]');
            if (hiddenInputs.length > 0) {
                this.produtoHiddenInput = hiddenInputs[0]; // Sempre o primeiro
                
                // 🔧 IMPORTANTE: Remover campos duplicados se existirem
                if (hiddenInputs.length > 1) {
                    console.log(`⚠️ Removendo ${hiddenInputs.length - 1} campos duplicados`);
                    for (let i = 1; i < hiddenInputs.length; i++) {
                        hiddenInputs[i].remove();
                    }
                }
            }
        }
        
        if (!this.produtoHiddenInput) {
            console.error('Campo hidden de produto não encontrado');
        }
    }
    
    attachEvents() {
        // Input de texto
        this.input.addEventListener('input', (e) => {
            clearTimeout(this.timeout);
            this.timeout = setTimeout(() => {
                this.buscarProdutos(e.target.value);
            }, 300);
        });
        
        // Foco
        this.input.addEventListener('focus', () => {
            if (this.produtos.length > 0) {
                this.showDropdown();
            }
        });
        
        // Fechar dropdown ao clicar fora
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        // Limpar seleção se texto for alterado manualmente
        this.input.addEventListener('input', () => {
            if (this.produtoHiddenInput && this.produtoHiddenInput.value) {
                // Se o texto não corresponde ao produto selecionado, limpar
                const produtoSelecionado = this.produtos.find(p => p.id == this.produtoHiddenInput.value);
                if (!produtoSelecionado || this.input.value !== produtoSelecionado.texto_completo) {
                    this.produtoHiddenInput.value = '';
                }
            }
        });
    }

    async buscarProdutos(termo) {
        console.log('🔍 Iniciando busca para termo:', termo);
        
        if (termo.length < 2) {
            console.log('⚠️ Termo muito curto, escondendo dropdown');
            this.hideDropdown();
            return;
        }
        
        try {
            const url = `/producao/api/buscar-produtos/?q=${encodeURIComponent(termo)}`;
            console.log('🌐 Fazendo requisição para:', url);
            
            const response = await fetch(url);
            console.log('📡 Resposta recebida:', response.status);
            
            const data = await response.json();
            console.log('📄 Dados recebidos:', data);
            
            // MODIFICAÇÃO: Aceitar tanto o formato atual quanto o esperado
            if (data.success || data.produtos) {
                this.produtos = data.produtos || [];
                
                // Adicionar o campo texto_completo se não existir
                this.produtos = this.produtos.map(produto => ({
                    ...produto,
                    texto_completo: produto.texto_completo || `${produto.codigo} - ${produto.nome}`
                }));
                
                console.log('✅ Produtos encontrados:', this.produtos.length);
                this.renderDropdown();
                this.showDropdown();
            } else {
                console.log('❌ API retornou erro:', data.error);
            }
        } catch (error) {
            console.error('💥 Erro ao buscar produtos:', error);
        }
    }
    
    renderDropdown() {
        console.log('🎨 Renderizando dropdown com', this.produtos.length, 'produtos');
        console.log('📦 Elemento dropdown:', this.dropdown);
        
        if (this.produtos.length === 0) {
            this.dropdown.innerHTML = '<div class="produto-search-item no-results">Nenhum produto encontrado</div>';
            return;
        }
        
        const html = this.produtos.map(produto => `
            <div class="produto-search-item" data-produto-id="${produto.id}">
                <div class="produto-codigo"><strong>${produto.codigo}</strong></div>
                <div class="produto-nome">${produto.nome}</div>
                <div class="produto-info">
                    <small class="text-muted">
                        ${produto.grupo || ''} ${produto.subgrupo ? '- ' + produto.subgrupo : ''}
                        | ${produto.unidade_medida || produto.unidade || ''}
                        ${produto.custo_medio ? '| R$ ' + produto.custo_medio.toFixed(2) : ''}
                    </small>
                </div>
            </div>
        `).join('');
        
        this.dropdown.innerHTML = html;
        console.log('✅ HTML do dropdown definido, length:', html.length);
        console.log('🎯 Primeiro item HTML:', this.dropdown.firstElementChild);
        
        // Adicionar event listeners aos itens
        this.dropdown.querySelectorAll('.produto-search-item[data-produto-id]').forEach(item => {
            item.addEventListener('click', () => {
                this.selecionarProduto(item.dataset.produtoId);
            });
        });
        
        console.log('🎯 Event listeners dos itens adicionados');
    }

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'produto-search-dropdown';
        
        // CSS mais simples e direto
        this.dropdown.style.cssText = `
            position: fixed !important;
            background: white !important;
            border: 2px solid #007bff !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
            max-height: 300px !important;
            overflow-y: auto !important;
            z-index: 99999 !important;
            display: none !important;
            min-width: 300px !important;
        `;
        
        // Inserir no body para evitar problemas de overflow
        document.body.appendChild(this.dropdown);
        
        console.log('📦 Dropdown criado e inserido no body');
    }

    showDropdown() {
        console.log('👁️ Mostrando dropdown');
        
        // Calcular posição baseada no input
        const inputRect = this.input.getBoundingClientRect();
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight,
            scrollY: window.scrollY,
            scrollX: window.scrollX
        };
        
        console.log('📍 Input position:', inputRect);
        console.log('🖥️ Viewport:', viewport);
        
        // Determinar onde posicionar (acima ou abaixo do input)
        const dropdownHeight = 300; // altura máxima
        const spaceBelow = viewport.height - inputRect.bottom;
        const spaceAbove = inputRect.top;
        
        let top, maxHeight;
        
        if (spaceBelow >= 200) {
            // Mostrar abaixo
            top = inputRect.bottom + 2;
            maxHeight = Math.min(dropdownHeight, spaceBelow - 10);
            console.log('⬇️ Mostrando abaixo do input');
        } else if (spaceAbove >= 200) {
            // Mostrar acima
            maxHeight = Math.min(dropdownHeight, spaceAbove - 10);
            top = inputRect.top - maxHeight - 2;
            console.log('⬆️ Mostrando acima do input');
        } else {
            // Forçar na viewport - usar o maior espaço disponível
            if (spaceBelow > spaceAbove) {
                top = inputRect.bottom + 2;
                maxHeight = spaceBelow - 10;
            } else {
                maxHeight = spaceAbove - 10;
                top = inputRect.top - maxHeight - 2;
            }
            console.log('📐 Ajustando para caber na viewport');
        }
        
        // Posição horizontal
        let left = inputRect.left;
        const dropdownWidth = Math.max(inputRect.width, 300);
        
        // Ajustar se sair da tela horizontalmente
        if (left + dropdownWidth > viewport.width) {
            left = viewport.width - dropdownWidth - 10;
            console.log('⬅️ Ajustado horizontalmente');
        }
        
        // Garantir que não saia pela esquerda
        if (left < 10) {
            left = 10;
            console.log('➡️ Ajustado para não sair pela esquerda');
        }
        
        // Aplicar estilos
        this.dropdown.style.left = left + 'px';
        this.dropdown.style.top = top + 'px';
        this.dropdown.style.width = dropdownWidth + 'px';
        this.dropdown.style.maxHeight = maxHeight + 'px';
        this.dropdown.style.display = 'block';
        
        console.log('✅ Dropdown posicionado:', {
            left: left,
            top: top,
            width: dropdownWidth,
            maxHeight: maxHeight
        });
        
        // SCROLL AUTOMÁTICO se necessário
        this.scrollToDropdownIfNeeded(inputRect, top, maxHeight);
    }

    scrollToDropdownIfNeeded(inputRect, dropdownTop, dropdownHeight) {
        const viewport = {
            height: window.innerHeight,
            scrollY: window.scrollY
        };
        
        const dropdownBottom = dropdownTop + dropdownHeight;
        const viewportBottom = viewport.scrollY + viewport.height;
        const viewportTop = viewport.scrollY;
        
        let needsScroll = false;
        let scrollTo = viewport.scrollY;
        
        // Verificar se dropdown está abaixo da viewport
        if (dropdownBottom > viewportBottom) {
            scrollTo = dropdownBottom - viewport.height + 20;
            needsScroll = true;
            console.log('📜 Scroll necessário para baixo:', scrollTo);
        }
        
        // Verificar se dropdown está acima da viewport  
        if (dropdownTop < viewportTop) {
            scrollTo = dropdownTop - 20;
            needsScroll = true;
            console.log('📜 Scroll necessário para cima:', scrollTo);
        }
        
        // Fazer scroll suave se necessário
        if (needsScroll) {
            window.scrollTo({
                top: scrollTo,
                behavior: 'smooth'
            });
            console.log('✅ Scroll automático executado');
        }
    }

    hideDropdown() {
        console.log('🙈 Escondendo dropdown');
        this.dropdown.style.display = 'none';
    }
   
    selecionarProduto(produtoId) {
        const produto = this.produtos.find(p => p.id == produtoId);
        if (produto) {
            // Atualizar campo de busca
            this.input.value = produto.texto_completo;
            
            // Atualizar campo hidden
            if (this.produtoHiddenInput) {
                this.produtoHiddenInput.value = produto.id;
            }
            
            // Preencher valor unitário se disponível
            if (produto.custo_medio) {
                const valorUnitarioInput = this.input.closest('tr').querySelector('input[name*="-valor_unitario"]');
                if (valorUnitarioInput && !valorUnitarioInput.value) {
                    valorUnitarioInput.value = produto.custo_medio.toFixed(2).replace('.', ',');
                }
            }
            
            // Fechar dropdown
            this.hideDropdown();
            
            // Trigger para recalcular totais
            this.input.dispatchEvent(new Event('produto-selecionado', { bubbles: true }));
        }
    }
    
    
    hideDropdown() {
        this.dropdown.style.display = 'none';
    }
}

// Inicializar automaticamente
document.addEventListener('DOMContentLoaded', function() {
    initProdutoSearch();
});

// Função para inicializar busca de produtos
function initProdutoSearch() {
    console.log('🔧 Procurando inputs de busca de produtos...');
    
    document.querySelectorAll('.produto-search-input').forEach(input => {
        console.log('🎯 Encontrado input:', input);
        
        // Verificar se já tem uma instância
        if (!input.produtoSearchInstance) {
            const row = input.closest('tr');
            const hiddenInput = row ? row.querySelector('input[name*="-produto"]') : null;
            
            // Se é um item existente (tem valor no hidden), marcar como válido
            if (hiddenInput && hiddenInput.value && input.value) {
                input.classList.add('is-valid');
                console.log('✅ Item existente detectado e marcado como válido:', input.value);
            }
            
            input.produtoSearchInstance = new ProdutoSearch(input);
        }
    });
}

// Função para inicializar em novos itens do formset
function initProdutoSearchInNewRow(row) {
    const input = row.querySelector('.produto-search-input');
    if (input && !input.produtoSearchInstance) {
        input.produtoSearchInstance = new ProdutoSearch(input);
    }
}