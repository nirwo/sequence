export class UiService {
    static #systemCardTemplate;
    static #systemsContainer;
    static #toastContainer;

    static initialize() {
        this.#systemCardTemplate = document.getElementById('systemCardTemplate');
        this.#systemsContainer = document.getElementById('systemsContainer');

        if (!this.#systemCardTemplate || !this.#systemsContainer) {
            throw new Error('Required DOM elements not found');
        }
    }

    static ensureToastContainer() {
        if (this.#toastContainer) return this.#toastContainer;

        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        this.#toastContainer = container;
        return container;
    }

    static showToast(message, type = 'success', duration = 5000) {
        const container = this.ensureToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white border-0 ${type === 'error' ? 'bg-danger' : 'bg-success'}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, {
            animation: true,
            autohide: true,
            delay: duration
        });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
            if (container.children.length === 0) {
                container.remove();
                this.#toastContainer = null;
            }
        });
    }

    static createSystemCard(system) {
        if (!this.#systemCardTemplate) return null;

        try {
            const clone = document.importNode(this.#systemCardTemplate.content, true);
            const card = clone.querySelector('.card');
            if (!card) return null;

            card.setAttribute('data-system-id', system._id);

            // Set system name and status
            const elements = {
                '.system-name': system.name || 'Unnamed System',
                '.status-badge': system.status ? 'Online' : 'Offline',
                '.status-text': `${system.name || 'System'} is ${system.status ? 'online' : 'offline'}`,
                '.app-name': system.app_name || 'N/A',
                '.target': system.target || 'N/A',
                '.check-type': system.check_type || 'ping',
                '.database': system.db_type !== 'N/A' ? `${system.db_type} (${system.db_name})` : 'N/A',
                '.owner': system.owner || 'N/A'
            };

            Object.entries(elements).forEach(([selector, value]) => {
                const element = clone.querySelector(selector);
                if (element) {
                    if (selector === '.status-badge') {
                        element.className = `status-badge badge ${system.status ? 'bg-success' : 'bg-danger'}`;
                    }
                    element.textContent = value;
                }
            });

            this.#setupClusterNodes(clone, system);
            this.#setupButtons(clone, system._id);

            return clone;
        } catch (error) {
            console.error('Error creating system card:', error);
            return null;
        }
    }

    static #setupClusterNodes(clone, system) {
        const clusterNodesDiv = clone.querySelector('.cluster-nodes');
        if (clusterNodesDiv && system.cluster_nodes?.length) {
            const nodesHtml = `
                <p class="mb-2"><strong>Cluster Nodes:</strong></p>
                <ul class="list-unstyled">
                    ${system.cluster_nodes.map(node => `
                        <li>
                            <i class="fas fa-server me-2"></i>
                            ${node.host}
                            <span class="badge ${node.status ? 'bg-success' : 'bg-danger'} ms-2">
                                ${node.status ? 'Online' : 'Offline'}
                            </span>
                        </li>
                    `).join('')}
                </ul>
            `;
            clusterNodesDiv.innerHTML = nodesHtml;
        }
    }

    static #setupButtons(clone, systemId) {
        const buttons = {
            '.test-btn': () => window.dispatchEvent(new CustomEvent('system:test', { detail: { systemId } })),
            '.edit-btn': () => window.dispatchEvent(new CustomEvent('system:edit', { detail: { systemId } })),
            '.delete-btn': () => window.dispatchEvent(new CustomEvent('system:delete', { detail: { systemId } }))
        };

        Object.entries(buttons).forEach(([selector, handler]) => {
            const button = clone.querySelector(selector);
            if (button) {
                if (selector === '.test-btn') {
                    button.innerHTML = `
                        <i class="fas fa-sync-alt loading-spinner" style="display: none;"></i>
                        Test Now
                    `;
                }
                button.addEventListener('click', handler);
            }
        });
    }

    static updateSystemStatus(systemId, status) {
        const systemCard = document.querySelector(`[data-system-id="${systemId}"]`);
        if (!systemCard) return;

        const elements = {
            statusBadge: systemCard.querySelector('.status-badge'),
            statusText: systemCard.querySelector('.status-text'),
            loadingSpinner: systemCard.querySelector('.loading-spinner'),
            testBtn: systemCard.querySelector('.test-btn')
        };

        if (elements.loadingSpinner) {
            elements.loadingSpinner.style.display = 'none';
        }

        if (elements.testBtn) {
            elements.testBtn.innerHTML = `
                <i class="fas fa-sync-alt loading-spinner" style="display: none;"></i>
                Test Now
            `;
        }

        if (elements.statusBadge) {
            elements.statusBadge.className = `status-badge badge ${status ? 'bg-success' : 'bg-danger'}`;
            elements.statusBadge.textContent = status ? 'Online' : 'Offline';
        }

        if (elements.statusText) {
            const systemName = systemCard.querySelector('.system-name')?.textContent || 'System';
            elements.statusText.textContent = `${systemName} is ${status ? 'online' : 'offline'}`;
        }
    }

    static clearSystemsContainer() {
        if (this.#systemsContainer) {
            this.#systemsContainer.innerHTML = '';
        }
    }

    static showEmptyState() {
        if (this.#systemsContainer) {
            this.#systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-muted">No systems found. Add a system to get started.</p>
                </div>
            `;
        }
    }

    static showErrorState(error) {
        if (this.#systemsContainer) {
            this.#systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-danger">Error loading systems: ${error}</p>
                </div>
            `;
        }
    }

    static getSystemsContainer() {
        return this.#systemsContainer;
    }
}
