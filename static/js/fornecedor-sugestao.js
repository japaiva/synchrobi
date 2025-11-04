/**
 * Módulo de Sugestão Inteligente de Fornecedores
 *
 * Funcionalidades:
 * - Busca fornecedores similares ao nome digitado/extraído
 * - Mostra modal de confirmação com sugestões
 * - Permite ao usuário escolher entre sugestões ou criar novo
 * - Integra com API de sugestões
 */

const FornecedorSugestao = {
    // Configurações
    config: {
        minScore: 0.60,  // Score mínimo para sugestões (60%)
        debounceDelay: 500,  // Delay para busca automática (ms)
        apiUrl: '/gestor/api/fornecedor/sugerir/',
    },

    // Estado
    state: {
        debounceTimer: null,
        ultimaBusca: '',
        sugestoesAtuais: [],
    },

    /**
     * Inicializa o módulo
     *
     * @param {Object} options - Opções de configuração
     * @param {string} options.inputSelector - Seletor do campo de nome do fornecedor
     * @param {string} options.fieldFornecedorSelector - Seletor do campo oculto de fornecedor
     * @param {boolean} options.autoSuggest - Se deve sugerir automaticamente ao digitar
     */
    init(options = {}) {
        // Mesclar configurações
        this.config = { ...this.config, ...options };

        // Configurar event listeners se autoSuggest estiver ativo
        if (this.config.autoSuggest && this.config.inputSelector) {
            this.setupAutoSuggest();
        }

        // Criar modal se não existir
        this.createModal();
    },

    /**
     * Configura sugestão automática ao digitar
     */
    setupAutoSuggest() {
        const input = document.querySelector(this.config.inputSelector);
        if (!input) return;

        input.addEventListener('input', (e) => {
            const nome = e.target.value.trim();

            // Limpar timer anterior
            clearTimeout(this.state.debounceTimer);

            // Se nome muito curto, não buscar
            if (nome.length < 3) {
                return;
            }

            // Debounce: aguardar usuário parar de digitar
            this.state.debounceTimer = setTimeout(() => {
                this.buscarSugestoes(nome);
            }, this.config.debounceDelay);
        });

        // Ao perder foco, verificar se tem sugestões
        input.addEventListener('blur', (e) => {
            const nome = e.target.value.trim();
            if (nome.length >= 3 && nome !== this.state.ultimaBusca) {
                setTimeout(() => {
                    this.buscarSugestoes(nome);
                }, 300);
            }
        });
    },

    /**
     * Busca sugestões de fornecedores similares
     *
     * @param {string} nome - Nome para buscar
     * @param {boolean} showModal - Se deve mostrar modal automaticamente
     */
    async buscarSugestoes(nome, showModal = true) {
        if (!nome || nome.length < 3) {
            console.warn('Nome muito curto para buscar sugestões');
            return null;
        }

        // Evitar buscas duplicadas
        if (nome === this.state.ultimaBusca) {
            return this.state.sugestoesAtuais;
        }

        try {
            const url = new URL(this.config.apiUrl, window.location.origin);
            url.searchParams.append('nome', nome);
            url.searchParams.append('min_score', this.config.minScore);
            url.searchParams.append('limit', 5);

            const response = await fetch(url);
            const data = await response.json();

            if (!data.success) {
                console.error('Erro ao buscar sugestões:', data.error || data.message);
                return null;
            }

            // Salvar estado
            this.state.ultimaBusca = nome;
            this.state.sugestoesAtuais = data.sugestoes || [];

            // Mostrar modal se houver sugestões e showModal = true
            if (showModal && this.state.sugestoesAtuais.length > 0) {
                this.mostrarModal(nome, this.state.sugestoesAtuais);
            }

            return data;

        } catch (error) {
            console.error('Erro ao buscar sugestões:', error);
            return null;
        }
    },

    /**
     * Cria o modal de sugestões no DOM
     */
    createModal() {
        // Verificar se modal já existe
        if (document.getElementById('modalSugestaoFornecedor')) {
            return;
        }

        const modalHtml = `
            <div class="modal fade" id="modalSugestaoFornecedor" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-search"></i>
                                Fornecedor Similar Encontrado
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info mb-3">
                                <strong>Nome detectado:</strong> <span id="nomeDetectado"></span>
                            </div>

                            <p class="mb-3">
                                Encontramos <strong id="totalSugestoes">0</strong> fornecedor(es) similar(es) já cadastrado(s).
                                Deseja usar algum deles?
                            </p>

                            <div id="listaSugestoes" class="list-group mb-3">
                                <!-- Sugestões serão inseridas aqui via JavaScript -->
                            </div>

                            <div class="alert alert-secondary">
                                <strong>Ou criar novo fornecedor:</strong>
                                <p class="mb-0 mt-2">
                                    Se nenhum dos fornecedores acima for o correto, você pode criar um novo fornecedor
                                    com o nome detectado.
                                </p>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="bi bi-x-circle"></i> Cancelar
                            </button>
                            <button type="button" class="btn btn-success" id="btnCriarNovoFornecedor">
                                <i class="bi bi-plus-circle"></i> Criar Novo Fornecedor
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Adicionar modal ao body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Configurar evento de criar novo fornecedor
        document.getElementById('btnCriarNovoFornecedor').addEventListener('click', () => {
            this.criarNovoFornecedor();
        });
    },

    /**
     * Mostra o modal com as sugestões
     *
     * @param {string} nomeDetectado - Nome que foi detectado
     * @param {Array} sugestoes - Array de sugestões
     */
    mostrarModal(nomeDetectado, sugestoes) {
        // Preencher informações
        document.getElementById('nomeDetectado').textContent = nomeDetectado.toUpperCase();
        document.getElementById('totalSugestoes').textContent = sugestoes.length;

        // Limpar lista anterior
        const listaSugestoes = document.getElementById('listaSugestoes');
        listaSugestoes.innerHTML = '';

        // Adicionar cada sugestão
        sugestoes.forEach((sugestao, index) => {
            const scorePercent = sugestao.score_percent;
            const scoreClass = scorePercent >= 80 ? 'success' : scorePercent >= 60 ? 'warning' : 'secondary';

            const itemHtml = `
                <button type="button" class="list-group-item list-group-item-action"
                        data-codigo="${sugestao.codigo}"
                        onclick="FornecedorSugestao.selecionarSugestao('${sugestao.codigo}')">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">
                                <span class="badge bg-${scoreClass} me-2">${scorePercent}% similar</span>
                                ${sugestao.razao_social}
                            </h6>
                            <p class="mb-1 text-muted small">
                                <strong>Código:</strong> ${sugestao.codigo}
                                ${sugestao.cnpj_cpf ? ` | <strong>CNPJ/CPF:</strong> ${sugestao.cnpj_cpf}` : ''}
                            </p>
                            ${sugestao.nome_fantasia ? `<p class="mb-0 text-muted small"><strong>Nome Fantasia:</strong> ${sugestao.nome_fantasia}</p>` : ''}
                            ${sugestao.criado_automaticamente ? '<span class="badge bg-secondary">Criado Automaticamente</span>' : ''}
                        </div>
                        <div class="ms-3">
                            <i class="bi bi-check-circle text-${scoreClass}" style="font-size: 1.5rem;"></i>
                        </div>
                    </div>
                </button>
            `;

            listaSugestoes.insertAdjacentHTML('beforeend', itemHtml);
        });

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('modalSugestaoFornecedor'));
        modal.show();
    },

    /**
     * Callback quando usuário seleciona uma sugestão
     *
     * @param {string} codigoFornecedor - Código do fornecedor selecionado
     */
    selecionarSugestao(codigoFornecedor) {
        console.log('Fornecedor selecionado:', codigoFornecedor);

        // Encontrar a sugestão selecionada
        const sugestao = this.state.sugestoesAtuais.find(s => s.codigo === codigoFornecedor);
        if (!sugestao) {
            console.error('Sugestão não encontrada:', codigoFornecedor);
            return;
        }

        // Preencher campos do formulário
        this.preencherCampoFornecedor(sugestao);

        // Fechar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalSugestaoFornecedor'));
        modal.hide();

        // Callback customizado se definido
        if (this.config.onSelecionado) {
            this.config.onSelecionado(sugestao);
        }
    },

    /**
     * Preenche o campo de fornecedor no formulário
     *
     * @param {Object} fornecedor - Dados do fornecedor
     */
    preencherCampoFornecedor(fornecedor) {
        // Se houver seletor de campo configurado
        if (this.config.fieldFornecedorSelector) {
            const field = document.querySelector(this.config.fieldFornecedorSelector);
            if (field) {
                // Se for um SELECT
                if (field.tagName === 'SELECT') {
                    // Verificar se opção existe
                    let option = field.querySelector(`option[value="${fornecedor.codigo}"]`);

                    // Se não existir, criar
                    if (!option) {
                        option = new Option(
                            `${fornecedor.codigo} - ${fornecedor.razao_social}`,
                            fornecedor.codigo,
                            true,
                            true
                        );
                        field.add(option);
                    }

                    field.value = fornecedor.codigo;

                    // Disparar evento change
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                }
                // Se for INPUT
                else {
                    field.value = fornecedor.codigo;
                    field.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        }

        // Preencher campo de nome se houver
        if (this.config.inputSelector) {
            const inputNome = document.querySelector(this.config.inputSelector);
            if (inputNome) {
                inputNome.value = fornecedor.razao_social;
            }
        }
    },

    /**
     * Callback quando usuário escolhe criar novo fornecedor
     */
    criarNovoFornecedor() {
        console.log('Criar novo fornecedor com nome:', this.state.ultimaBusca);

        // Fechar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalSugestaoFornecedor'));
        modal.hide();

        // Callback customizado se definido
        if (this.config.onCriarNovo) {
            this.config.onCriarNovo(this.state.ultimaBusca);
        } else {
            // Comportamento padrão: manter o nome digitado e continuar
            alert(`Um novo fornecedor "${this.state.ultimaBusca}" será criado quando você salvar.`);
        }
    },

    /**
     * Método público para buscar e mostrar sugestões manualmente
     *
     * @param {string} nome - Nome para buscar
     */
    async mostrarSugestoesManual(nome) {
        const resultado = await this.buscarSugestoes(nome, false);

        if (!resultado || !resultado.success) {
            alert('Nenhum fornecedor similar encontrado.');
            return;
        }

        if (resultado.sugestoes.length === 0) {
            alert(`Nenhum fornecedor similar a "${nome}" foi encontrado. Você pode criar um novo.`);
            return;
        }

        this.mostrarModal(nome, resultado.sugestoes);
    }
};

// Exportar para uso global
window.FornecedorSugestao = FornecedorSugestao;
