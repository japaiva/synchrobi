// static/js/tree-manager-external.js
// Extensão do TreeManager para suportar contas externas

class TreeManagerExternal extends TreeManager {
    constructor(config) {
        super(config);
        this.systemFilter = '';
        this.externalStatusFilter = '';
        this.expandedExternals = new Set();
    }
    
    createNodeHTML(item, hasChildren, isExpanded, typeClass) {
        const typeBadge = item.tipo ? 
            `<span class="type-badge ${typeClass}">${item.tipo === 'A' ? 'Analítico' : 'Sintético'}</span>` : '';
        
        const empresaInfo = this.config.hasCompanyField && item.empresa_sigla ? 
            `<small class="text-muted ms-2">(${item.empresa_sigla})</small>` : '';
        
        const actionButtons = this.createActionButtons(item);
        
        // Informações de contas externas
        const externalInfo = this.createExternalAccountsHTML(item);
        const hasExternalsClass = item.contas_externas && item.contas_externas.length > 0 ? 'has-externals' : '';
        
        return `
            <div class="tree-node level-${item.nivel} ${typeClass} ${hasExternalsClass}" data-codigo="${item.codigo}">
                <div class="tree-info">
                    <div class="tree-content">
                        ${hasChildren ? 
                            `<button class="tree-toggle ${isExpanded ? 'expanded' : ''}" onclick="treeManager.toggleNode(event, '${item.codigo}')">
                                <i class="fas fa-chevron-right"></i>
                            </button>` : 
                            '<span style="width: 22px; display: inline-block;"></span>'
                        }
                        <span class="tree-code">${this.escapeHtml(item.codigo)}</span>
                        <span class="tree-name">${this.escapeHtml(item.nome)}</span>
                        ${empresaInfo}
                        ${this.createExternalCountBadge(item)}
                    </div>
                    <div class="tree-badges">
                        ${typeBadge}
                        <div class="tree-actions">
                            ${this.createExternalActionButtons(item)}
                            ${actionButtons}
                        </div>
                    </div>
                </div>
                ${externalInfo}
            </div>
            ${hasChildren ? 
                `<ul class="tree-children ${isExpanded ? 'expanded' : 'collapsed'}"></ul>` : ''
            }
        `;
    }
    
    createExternalCountBadge(item) {
        if (!item.contas_externas || item.contas_externas.length === 0) {
            return '';
        }
        
        const count = item.contas_externas.length;
        const isExpanded = this.expandedExternals.has(item.codigo);
        
        return `
            <button class="toggle-externals ${isExpanded ? 'expanded' : ''}" 
                    onclick="toggleExternalAccounts(event, '${item.codigo}')"
                    title="${count} código(s) externo(s)">
                <i class="fas fa-${isExpanded ? 'eye-slash' : 'eye'}"></i>
                <span class="external-count-badge">${count}</span>
            </button>
        `;
    }
    
    createExternalActionButtons(item) {
        return `
            <button class="btn btn-sm btn-outline-info" 
                    onclick="addExternalAccount(event, '${item.codigo}')" 
                    title="Adicionar código externo">
                <i class="fas fa-link"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" 
                    onclick="openExternalAccountModal('${item.codigo}')" 
                    title="Gerenciar códigos externos">
                <i class="fas fa-cogs"></i>
            </button>
        `;
    }
    
    createExternalAccountsHTML(item) {
        if (!item.contas_externas || item.contas_externas.length === 0) {
            return '';
        }
        
        const isExpanded = this.expandedExternals.has(item.codigo);
        const displayClass = isExpanded ? '' : 'd-none';
        
        const externalItems = item.contas_externas.map(external => `
            <div class="external-account-item">
                <div class="d-flex align-items-center flex-grow-1">
                    <span class="external-code">${this.escapeHtml(external.codigo_externo)}</span>
                    <span class="external-name">${this.escapeHtml(external.nome_externo)}</span>
                    <span class="external-system">${this.escapeHtml(external.sistema_origem)}</span>
                </div>
                <div class="external-actions">
                    <button class="btn btn-xs btn-outline-primary" 
                            onclick="editExternalAccount(event, ${external.id})" 
                            title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-xs btn-outline-danger" 
                            onclick="deleteExternalAccount(event, ${external.id}, '${this.escapeHtml(external.codigo_externo)}')" 
                            title="Excluir">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                ${external.empresas_utilizacao ? `
                    <div class="companies-list">
                        <i class="fas fa-building"></i> ${this.escapeHtml(external.empresas_utilizacao)}
                    </div>
                ` : ''}
            </div>
        `).join('');
        
        return `
            <div class="external-accounts ${displayClass}">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <small class="text-muted">
                        <i class="fas fa-link me-1"></i>
                        Códigos Externos (${item.contas_externas.length})
                    </small>
                    <button class="btn btn-xs btn-outline-success" 
                            onclick="addExternalAccount(event, '${item.codigo}')" 
                            title="Adicionar código externo">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
                ${externalItems}
            </div>
        `;
    }
    
    filterRecursive(data, searchTerm, levelFilter, typeFilter) {
        const result = [];
        
        for (const item of data) {
            let matches = false;
            
            // Busca em campos básicos
            if (searchTerm) {
                matches = matches || 
                    item.codigo.toLowerCase().includes(searchTerm) ||
                    item.nome.toLowerCase().includes(searchTerm) ||
                    (item.descricao && item.descricao.toLowerCase().includes(searchTerm));
                
                // Busca em contas externas
                if (item.contas_externas) {
                    matches = matches || item.contas_externas.some(external => 
                        external.codigo_externo.toLowerCase().includes(searchTerm) ||
                        external.nome_externo.toLowerCase().includes(searchTerm) ||
                        external.sistema_origem.toLowerCase().includes(searchTerm) ||
                        (external.empresas_utilizacao && external.empresas_utilizacao.toLowerCase().includes(searchTerm))
                    );
                }
            } else {
                matches = true; // Se não há busca, todos passam na primeira fase
            }
            
            // Filtro por sistema
            if (this.systemFilter && matches) {
                if (item.contas_externas && item.contas_externas.length > 0) {
                    matches = item.contas_externas.some(external => 
                        external.sistema_origem.toLowerCase().includes(this.systemFilter.toLowerCase())
                    );
                } else {
                    matches = false;
                }
            }
            
            // Filtro por status de contas externas
            if (this.externalStatusFilter && matches) {
                if (this.externalStatusFilter === 'with') {
                    matches = item.contas_externas && item.contas_externas.length > 0;
                } else if (this.externalStatusFilter === 'without') {
                    matches = !item.contas_externas || item.contas_externas.length === 0;
                }
            }
            
            // Filtro por nível
            if (levelFilter && matches) {
                matches = item.nivel === parseInt(levelFilter);
            }
            
            // Filtro por tipo
            if (typeFilter && matches) {
                matches = item.tipo === typeFilter;
            }
            
            let filteredChildren = [];
            if (item.filhos && item.filhos.length > 0) {
                filteredChildren = this.filterRecursive(item.filhos, searchTerm, levelFilter, typeFilter);
            }
            
            if (matches || filteredChildren.length > 0) {
                result.push({ ...item, filhos: filteredChildren });
            }
        }
        
        return result;
    }
    
    filterBySystem(system) {
        this.systemFilter = system;
        this.applyAllFilters();
    }
    
    filterByExternalStatus(status) {
        this.externalStatusFilter = status;
        this.applyAllFilters();
    }
    
    applyAllFilters() {
        const searchTerm = document.getElementById('tree-search').value.toLowerCase();
        
        if (!searchTerm && !this.systemFilter && !this.externalStatusFilter) {
            this.filteredData = this.config.treeData;
        } else {
            this.filteredData = this.filterRecursive(this.config.treeData, searchTerm);
            if (searchTerm || this.systemFilter) {
                this.expandRelevantNodes(this.filteredData);
            }
        }
        
        this.renderTree(this.filteredData, document.getElementById('itemTree'));
        this.updateStats();
    }
    
    filterTree(searchTerm = '') {
        const searchInput = document.getElementById('tree-search');
        if (searchInput) {
            searchTerm = searchInput.value.toLowerCase();
        }
        
        this.applyAllFilters();
    }
    
    updateStats() {
        let totalItems = 0;
        let itemsWithExternal = 0;
        let totalExternalCodes = 0;
        let systems = new Set();
        
        function countRecursive(data) {
            data.forEach(item => {
                totalItems++;
                
                if (item.contas_externas && item.contas_externas.length > 0) {
                    itemsWithExternal++;
                    totalExternalCodes += item.contas_externas.length;
                    
                    item.contas_externas.forEach(external => {
                        if (external.sistema_origem) {
                            systems.add(external.sistema_origem);
                        }
                    });
                }
                
                if (item.filhos) {
                    countRecursive(item.filhos);
                }
            });
        }
        
        countRecursive(this.filteredData);
        
        // Atualizar elementos na tela
        const totalElement = document.getElementById('total-accounts');
        const withExternalElement = document.getElementById('accounts-with-external');
        const totalExternalElement = document.getElementById('total-external-codes');
        const systemsElement = document.getElementById('systems-count');
        
        if (totalElement) totalElement.textContent = totalItems;
        if (withExternalElement) withExternalElement.textContent = itemsWithExternal;
        if (totalExternalElement) totalExternalElement.textContent = totalExternalCodes;
        if (systemsElement) systemsElement.textContent = systems.size;
    }
    
    refreshTree() {
        const treeContainer = document.getElementById('itemTree');
        treeContainer.innerHTML = `
            <li class="tree-item">
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-2"></div>
                    <div class="text-muted">Atualizando árvore com códigos externos...</div>
                </div>
            </li>
        `;
        
        fetch(this.config.apiTreeDataUrl, {
            headers: { 'X-CSRFToken': this.config.csrfToken }
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.success) {
                this.config.treeData = data.tree_data;
                this.filteredData = data.tree_data;
                this.renderTree(this.filteredData, treeContainer);
                this.updateStats();
                this.showToast('Árvore atualizada com sucesso', 'success');
            } else {
                throw new Error(data.message || 'Erro na resposta da API');
            }
        })
        .catch(error => {
            treeContainer.innerHTML = `
                <li class="tree-item">
                    <div class="alert alert-danger text-center">
                        <i class="fas fa-exclamation-triangle mb-2"></i>
                        <div>Erro ao atualizar árvore: ${error.message}</div>
                        <button class="btn btn-sm btn-outline-danger mt-2" onclick="treeManager.refreshTree()">
                            <i class="fas fa-retry me-1"></i> Tentar Novamente
                        </button>
                    </div>
                </li>
            `;
            this.showToast('Erro ao atualizar: ' + error.message, 'error');
        });
    }
}

// Função global para alternar visualização de contas externas
window.toggleExternalAccounts = function(event, codigo) {
    event.stopPropagation();
    
    if (window.treeManager && window.treeManager.expandedExternals) {
        if (window.treeManager.expandedExternals.has(codigo)) {
            window.treeManager.expandedExternals.delete(codigo);
        } else {
            window.treeManager.expandedExternals.add(codigo);
        }
        
        // Re-renderizar apenas este nó
        const nodeElement = document.querySelector(`[data-codigo="${codigo}"]`);
        if (nodeElement) {
            // Encontrar o item nos dados
            function findItemInData(data, targetCodigo) {
                for (const item of data) {
                    if (item.codigo === targetCodigo) {
                        return item;
                    }
                    if (item.filhos) {
                        const found = findItemInData(item.filhos, targetCodigo);
                        if (found) return found;
                    }
                }
                return null;
            }
            
            const item = findItemInData(window.treeManager.filteredData, codigo);
            if (item) {
                // Re-criar HTML do nó
                const hasChildren = item.filhos && item.filhos.length > 0;
                const isExpanded = window.treeManager.expandedNodes.has(item.codigo);
                const typeClass = item.tipo === 'A' ? 'analytic' : 'synthetic';
                
                nodeElement.outerHTML = window.treeManager.createNodeHTML(item, hasChildren, isExpanded, typeClass);
            }
        }
    }
};