// static/js/tree-manager.js - VERSÃO ATUALIZADA COM TRATAMENTO ESPECÍFICO PARA CONTAS EXTERNAS

class TreeManager {
    constructor(config) {
        this.config = {
            treeData: config.treeData || [],
            updateUrlBase: config.updateUrlBase,
            createUrl: config.createUrl,
            apiTreeDataUrl: config.apiTreeDataUrl,
            modalId: config.modalId,
            entityName: config.entityName || 'Item',
            csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            hasCompanyField: config.hasCompanyField || false,
            hasDetailModal: config.hasDetailModal || false,
            useId: config.useId || false,
            isDeclarativeHierarchy: config.isDeclarativeHierarchy || false,
            relatedTableConfig: config.relatedTableConfig || null,
            ...config
        };
        
        this.filteredData = this.config.treeData;
        this.expandedNodes = new Set();
        this.modal = null;
        this.renderTimeout = null;
        
        this.init();
    }
    
    init() {
        this.modal = new bootstrap.Modal(document.getElementById(this.config.modalId));
        this.renderTree(this.config.treeData, document.getElementById('itemTree'));
        
        document.getElementById('tree-search').addEventListener('input', 
            this.debounce(e => this.filterTree(e.target.value.toLowerCase()), 300)
        );
    }
    
    openCreateModal(event, codigoPai = null) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        let url = this.config.createUrl;
        if (codigoPai) {
            url += `?codigo_pai=${encodeURIComponent(codigoPai)}`;
        }
        
        this.loadModalContent(`Nova ${this.config.entityName}`, url);
    }
    
    openEditModal(event, identifier) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!identifier) {
            this.showToast('Erro: identificador não fornecido', 'error');
            return;
        }
        
        const url = `${this.config.updateUrlBase}${identifier}/editar/`;
        this.loadModalContent(`Editar ${this.config.entityName}`, url);
    }
    
    openDetailModal(event, id) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!this.config.hasDetailModal) return;
        
        const url = `${this.config.updateUrlBase}${id}/detalhes/`;
        this.loadModalContent(`Detalhes da ${this.config.entityName}`, url);
    }
    
    loadModalContent(title, url) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary mb-3"></div>
                <div>Carregando...</div>
            </div>
        `;
        
        this.modal.show();
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.config.csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.text();
        })
        .then(html => {
            document.getElementById('modalBody').innerHTML = html;
            this.setupModalForm();
        })
        .catch(error => {
            document.getElementById('modalBody').innerHTML = `
                <div class="alert alert-danger">
                    <h6>Erro ao carregar formulário</h6>
                    <p>Erro: ${error.message}</p>
                    <button class="btn btn-secondary" onclick="treeManager.modal.hide()">Fechar</button>
                </div>
            `;
        });
    }
    
    setupModalForm() {
        const form = document.querySelector(`#${this.config.modalId} form`);
        if (!form) return;
        
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Salvando...';
            submitBtn.disabled = true;
            
            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showToast(data.message, 'success');
                    this.modal.hide();
                    this.refreshTree();
                } else {
                    this.showToast(data.message || 'Erro ao salvar', 'error');
                    if (data.errors) {
                        this.showFormErrors(data.errors);
                    }
                }
            })
            .catch(error => {
                this.showToast('Erro ao salvar: ' + error.message, 'error');
            })
            .finally(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
    }
    
    showFormErrors(errors) {
        Object.keys(errors).forEach(field => {
            const input = document.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                
                const existingFeedback = input.parentNode.querySelector('.invalid-feedback');
                if (existingFeedback) {
                    existingFeedback.remove();
                }
                
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = errors[field].join(', ');
                input.parentNode.appendChild(feedback);
            }
        });
    }
    
    deleteItem(event, identifier, nome) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!confirm(`Tem certeza que deseja excluir "${nome}"?\n\nEsta ação não pode ser desfeita.`)) {
            return;
        }
        
        this.showLoadingOverlay(true);
        
        fetch(`${this.config.updateUrlBase}${identifier}/excluir/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.config.csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            this.showToast(data.message, data.success ? 'success' : 'error');
            if (data.success) this.refreshTree();
        })
        .catch(error => {
            this.showToast('Erro ao excluir: ' + error.message, 'error');
        })
        .finally(() => {
            this.showLoadingOverlay(false);
        });
    }
    
    renderTree(data, container) {
        if (this.renderTimeout) {
            clearTimeout(this.renderTimeout);
        }
        
        if (!data || !data.length) {
            container.innerHTML = `<li class="tree-item"><div class="alert alert-info text-center">Nenhuma ${this.config.entityName.toLowerCase()} encontrada.</div></li>`;
            return;
        }
        
        const fragment = document.createDocumentFragment();
        const batchSize = 50;
        let currentIndex = 0;
        
        const renderBatch = () => {
            const endIndex = Math.min(currentIndex + batchSize, data.length);
            
            for (let i = currentIndex; i < endIndex; i++) {
                const nodeElement = this.createTreeNode(data[i]);
                fragment.appendChild(nodeElement);
            }
            
            currentIndex = endIndex;
            
            if (currentIndex < data.length) {
                requestAnimationFrame(renderBatch);
            } else {
                container.innerHTML = '';
                container.appendChild(fragment);
            }
        };
        
        requestAnimationFrame(renderBatch);
    }
    
    createTreeNode(item) {
        const li = document.createElement('li');
        li.className = 'tree-item';
        
        const hasChildren = this.config.isDeclarativeHierarchy ? 
            (item.tem_filhos || (item.filhos && item.filhos.length > 0)) :
            (item.filhos && item.filhos.length > 0);
            
        const isExpanded = this.expandedNodes.has(item.codigo);
        const typeClass = item.tipo === 'A' ? 'analytic' : 'synthetic';
        
        li.innerHTML = this.createNodeHTML(item, hasChildren, isExpanded, typeClass);
        
        if (hasChildren && isExpanded && item.filhos) {
            const childrenUl = li.querySelector('.tree-children');
            if (childrenUl) {
                const childrenFragment = document.createDocumentFragment();
                item.filhos.forEach(filho => {
                    childrenFragment.appendChild(this.createTreeNode(filho));
                });
                childrenUl.appendChild(childrenFragment);
            }
        }
        
        return li;
    }
    
    createNodeHTML(item, hasChildren, isExpanded, typeClass) {
        const typeBadge = item.tipo ? 
            `<span class="type-badge ${typeClass}">${item.tipo === 'A' ? 'Analítico' : 'Sintético'}</span>` : '';
        
        const empresaInfo = this.config.hasCompanyField && item.empresa_sigla ? 
            `<small class="text-muted ms-2">(${item.empresa_sigla})</small>` : '';
        
        const nivelDisplay = this.config.isDeclarativeHierarchy ? item.nivel : this.calculateLevel(item.codigo);
        
        const actionButtons = this.createActionButtons(item);
        
        return `
            <div class="tree-node level-${nivelDisplay} ${typeClass}">
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
                    </div>
                    <div class="tree-badges">
                        ${typeBadge}
                        <div class="tree-actions">
                            ${actionButtons}
                        </div>
                    </div>
                </div>
            </div>
            ${hasChildren ? 
                `<ul class="tree-children ${isExpanded ? 'expanded' : 'collapsed'}"></ul>` : ''
            }
        `;
    }
    
    createActionButtons(item) {
        const identifier = this.config.useId ? item.id : item.codigo;
        let buttons = '';
        
        // 1. Botão Detalhes (condicional)
        if (this.config.hasDetailModal) {
            buttons += `
                <button class="btn btn-sm btn-outline-info" onclick="treeManager.openDetailModal(event, ${item.id})" title="Detalhes">
                    <i class="fas fa-eye"></i>
                </button>
            `;
        }
        
        // 2. Botão Editar (sempre presente)
        buttons += `
            <button class="btn btn-sm btn-outline-primary" onclick="treeManager.openEditModal(event, '${identifier}')" title="Editar">
                <i class="fas fa-edit"></i>
            </button>
        `;
        
        // 3. Botão para Tabela Relacionada - COM TRATAMENTO ESPECÍFICO PARA CONTAS EXTERNAS
        if (this.config.relatedTableConfig) {
            const config = this.config.relatedTableConfig;
            const configKey = config.configKey;
            
            // VERIFICAR SE É CONTAS EXTERNAS E SE EXISTE FUNÇÃO ESPECÍFICA
            if (configKey === 'external_codes' && typeof window.openExternalAccountModal === 'function') {
                // Usar implementação específica das contas externas
                buttons += `
                    <button class="btn btn-sm btn-outline-warning" 
                            onclick="window.openExternalAccountModal('${item.codigo}')" 
                            title="Códigos Externos">
                        <i class="fas fa-link"></i>
                    </button>
                `;
            } else {
                // Usar implementação genérica para outros casos
                const relatedConfig = window.relatedTableConfigs?.[configKey];
                if (relatedConfig) {
                    buttons += `
                        <button class="btn btn-sm ${relatedConfig.buttonClass || 'btn-outline-warning'}" 
                                onclick="openRelatedTableModal(event, '${item.codigo}', '${configKey}')" 
                                title="${relatedConfig.buttonLabel || 'Itens Relacionados'}">
                            <i class="${relatedConfig.buttonIcon || 'fas fa-list'}"></i>
                        </button>
                    `;
                }
            }
        }
        
        // 4. Botão Criar Sub-item (sempre presente)
        buttons += `
            <button class="btn btn-sm btn-outline-success" onclick="treeManager.openCreateModal(event, '${item.codigo}')" title="Sub-item">
                <i class="fas fa-plus"></i>
            </button>
        `;
        
        // 5. Botão Excluir (sempre presente)
        buttons += `
            <button class="btn btn-sm btn-outline-danger" onclick="treeManager.deleteItem(event, '${identifier}', '${this.escapeHtml(item.nome)}')" title="Excluir">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        return buttons;
    }
    
    toggleNode(event, codigo) {
        event.stopPropagation();
        
        if (this.expandedNodes.has(codigo)) {
            this.expandedNodes.delete(codigo);
        } else {
            this.expandedNodes.add(codigo);
        }
        
        this.renderTree(this.filteredData, document.getElementById('itemTree'));
    }
    
    filterTree(searchTerm = '') {
        if (!searchTerm) {
            this.filteredData = this.config.treeData;
        } else {
            this.filteredData = this.filterRecursive(this.config.treeData, searchTerm);
            if (searchTerm) this.expandRelevantNodes(this.filteredData);
        }
        
        this.renderTree(this.filteredData, document.getElementById('itemTree'));
    }
    
    filterRecursive(data, searchTerm) {
        const result = [];
        
        for (const item of data) {
            let matches = searchTerm && (
                item.codigo.toLowerCase().includes(searchTerm) ||
                item.nome.toLowerCase().includes(searchTerm) ||
                (item.descricao && item.descricao.toLowerCase().includes(searchTerm))
            );
            
            let filteredChildren = [];
            if (item.filhos && item.filhos.length > 0) {
                filteredChildren = this.filterRecursive(item.filhos, searchTerm);
            }
            
            if (matches || filteredChildren.length > 0) {
                result.push({ ...item, filhos: filteredChildren });
            }
        }
        
        return result;
    }
    
    expandRelevantNodes(data) {
        const expandRecursive = (items) => {
            for (const item of items) {
                if (item.filhos && item.filhos.length > 0) {
                    this.expandedNodes.add(item.codigo);
                    expandRecursive(item.filhos);
                }
            }
        };
        expandRecursive(data);
    }
    
    calculateLevel(codigo) {
        if (this.config.isDeclarativeHierarchy) {
            return 1; // Fallback, mas o nivel deve vir do item
        }
        return codigo.count('.') + 1;
    }
    
    refreshTree() {
        const treeContainer = document.getElementById('itemTree');
        treeContainer.innerHTML = `
            <li class="tree-item">
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-2"></div>
                    <div class="text-muted">Atualizando árvore...</div>
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
    
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
        
        const toastId = 'toast-' + Date.now();
        
        const bgClass = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        }[type] || 'bg-info';
        
        const icon = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        }[type] || 'info-circle';
        
        toastContainer.insertAdjacentHTML('beforeend', `
            <div class="toast ${bgClass} text-white" id="${toastId}" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${icon} me-2"></i>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        const toastElement = document.getElementById(toastId);
        if (toastElement) {
            const toast = new bootstrap.Toast(toastElement, { delay: 4000 });
            toast.show();
            
            setTimeout(() => {
                if (toastElement && toastElement.parentNode) {
                    toastElement.remove();
                }
            }, 5000);
        }
    }
    
    showLoadingOverlay(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            if (show) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }
    }
    
    debounce(func, wait) {
        return (...args) => {
            const later = () => {
                clearTimeout(this.renderTimeout);
                func(...args);
            };
            clearTimeout(this.renderTimeout);
            this.renderTimeout = setTimeout(later, wait);
        };
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ===== SISTEMA GENÉRICO PARA TABELAS RELACIONADAS =====

// FUNÇÃO GENÉRICA para abrir modal de tabela relacionada
window.openRelatedTableModal = function(event, parentCode, configKey) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Buscar configuração específica
    const configs = window.relatedTableConfigs || {};
    const config = configs[configKey];
    
    if (!config) {
        console.error(`Configuração '${configKey}' não encontrada`);
        return;
    }
    
    // Criar modal genérico se não existir
    let modalId = `relatedTableModal_${configKey}`;
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        document.body.insertAdjacentHTML('beforeend', `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog ${config.modalSize || 'modal-lg'}">
                    <div class="modal-content">
                        <div class="modal-header ${config.headerClass || 'bg-primary text-white'}">
                            <h5 class="modal-title" id="${modalId}Title">
                                <i class="${config.buttonIcon || 'fas fa-list'} me-2"></i>${config.modalTitle || 'Itens Relacionados'}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="${modalId}Body">
                            <div class="text-center py-4">
                                <div class="spinner-border text-primary mb-3"></div>
                                <div>Carregando...</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>Fechar
                            </button>
                            <button type="button" class="btn btn-success" onclick="addNewRelatedItem('${parentCode}', '${configKey}')">
                                <i class="fas fa-plus me-1"></i> ${config.addButtonLabel || 'Novo Item'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);
        modal = document.getElementById(modalId);
    }
    
    const title = document.getElementById(`${modalId}Title`);
    const body = document.getElementById(`${modalId}Body`);
    
    title.innerHTML = `<i class="${config.buttonIcon} me-2"></i>${config.modalTitle} - ${parentCode}`;
    body.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary mb-3"></div>
            <div>Carregando ${config.modalTitle.toLowerCase()} de <strong>${parentCode}</strong>...</div>
        </div>
    `;
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Montar URL com parâmetro
    const url = `${config.listUrl}?${config.parameterName}=${encodeURIComponent(parentCode)}`;
    
    // Carregar dados via AJAX
    fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        return response.text();
    })
    .then(html => {
        body.innerHTML = html;
    })
    .catch(error => {
        body.innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>Erro ao carregar ${config.modalTitle.toLowerCase()}</h6>
                <p class="mb-2">Erro: ${error.message}</p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-danger" onclick="openRelatedTableModal(null, '${parentCode}', '${configKey}')">
                        <i class="fas fa-retry me-1"></i> Tentar Novamente
                    </button>
                    <button class="btn btn-sm btn-success" onclick="addNewRelatedItem('${parentCode}', '${configKey}')">
                        <i class="fas fa-plus me-1"></i> ${config.addButtonLabel || 'Criar Novo'}
                    </button>
                </div>
            </div>
        `;
    });
};

// FUNÇÃO GENÉRICA para adicionar novo item relacionado
window.addNewRelatedItem = function(parentCode, configKey) {
    const configs = window.relatedTableConfigs || {};
    const config = configs[configKey];
    
    if (!config) {
        console.error(`Configuração '${configKey}' não encontrada`);
        return;
    }
    
    const url = `${config.createUrl}?${config.parameterName}=${encodeURIComponent(parentCode)}`;
    
    if (config.openInNewTab) {
        window.open(url, '_blank', 'width=900,height=700,scrollbars=yes,resizable=yes');
    } else {
        window.location.href = url;
    }
};

// FUNÇÃO ESPECÍFICA PARA CONTAS EXTERNAS - MANTER COMPATIBILIDADE
window.openExternalAccountModal = function(contaCodigo) {
    const modalId = 'relatedTableModal_external_codes';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        // Criar modal se não existir
        document.body.insertAdjacentHTML('beforeend', `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="fas fa-link me-2"></i>Códigos Externos - ${contaCodigo}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="${modalId}Body">
                            <div class="text-center py-4">
                                <div class="spinner-border text-primary mb-3"></div>
                                <div>Carregando códigos externos...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
        modal = document.getElementById(modalId);
    }
    
    const body = document.getElementById(`${modalId}Body`);
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Carregar conteúdo específico
    fetch(`/gestor/contas-externas/?conta=${encodeURIComponent(contaCodigo)}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        return response.text();
    })
    .then(html => {
        body.innerHTML = html;
    })
    .catch(error => {
        body.innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>Erro ao carregar códigos externos</h6>
                <p class="mb-2">Erro: ${error.message}</p>
                <button class="btn btn-sm btn-outline-danger" onclick="window.openExternalAccountModal('${contaCodigo}')">
                    <i class="fas fa-retry me-1"></i> Tentar Novamente
                </button>
            </div>
        `;
    });
};

// CONFIGURAÇÕES GLOBAIS para diferentes tipos de tabelas relacionadas
window.relatedTableConfigs = {
    // Códigos Externos para Contas Contábeis - SERÁ IGNORADO EM FAVOR DA FUNÇÃO ESPECÍFICA
    "external_codes": {
        buttonLabel: "Códigos Externos",
        buttonIcon: "fas fa-link",
        buttonClass: "btn-outline-warning",
        modalTitle: "Códigos Externos",
        modalSize: "modal-lg",
        headerClass: "bg-warning text-dark",
        listUrl: "/gestor/contas-externas/",
        createUrl: "/gestor/contas-externas/nova/",
        parameterName: "conta",
        addButtonLabel: "Novo Código Externo",
        openInNewTab: true
    },
    
    // Responsáveis por Unidade
    "unit_managers": {
        buttonLabel: "Responsáveis",
        buttonIcon: "fas fa-users",
        buttonClass: "btn-outline-info",
        modalTitle: "Responsáveis da Unidade",
        modalSize: "modal-md",
        headerClass: "bg-info text-white",
        listUrl: "/gestor/unidade-responsaveis/",
        createUrl: "/gestor/unidade-responsaveis/novo/",
        parameterName: "unidade",
        addButtonLabel: "Novo Responsável",
        openInNewTab: false
    },
    
    // Orçamentos por Centro de Custo
    "cost_center_budgets": {
        buttonLabel: "Orçamentos",
        buttonIcon: "fas fa-chart-line",
        buttonClass: "btn-outline-success",
        modalTitle: "Orçamentos do Centro de Custo",
        modalSize: "modal-xl",
        headerClass: "bg-success text-white",
        listUrl: "/gestor/centro-custo-orcamentos/",
        createUrl: "/gestor/centro-custo-orcamentos/novo/",
        parameterName: "centro_custo",
        addButtonLabel: "Novo Orçamento",
        openInNewTab: false
    }
};