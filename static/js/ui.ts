class UiService {
    private static systemCardTemplate: HTMLTemplateElement;
    private static systemsContainer: HTMLElement;
    private static toastContainer: HTMLElement;

    static initialize() {
        this.systemCardTemplate = document.getElementById('systemCardTemplate') as HTMLTemplateElement;
        this.systemsContainer = document.getElementById('systemsContainer') as HTMLElement;
        this.ensureToastContainer();

        if (!this.systemCardTemplate || !this.systemsContainer) {
            throw new Error('Required DOM elements not found');
        }
    }

    private static ensureToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        this.toastContainer = container;
    }

    static showToast(message: string, type: 'success' | 'error' = 'success', duration = 5000) {
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

        this.toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, {
            animation: true,
            autohide: true,
            delay: duration
        });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
            if (this.toastContainer.children.length === 0) {
                this.toastContainer.remove();
            }
        });
    }

    static createSystemCard(system: System): DocumentFragment | null {
        try {
            const clone = document.importNode(this.systemCardTemplate.content, true);
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

            // Set up cluster nodes
            this.setupClusterNodes(clone, system);
            this.setupButtons(clone, system._id);

            return clone;
        } catch (error) {
            console.error('Error creating system card:', error);
            return null;
        }
    }

    private static setupClusterNodes(clone: DocumentFragment, system: System) {
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

    private static setupButtons(clone: DocumentFragment, systemId: string) {
        const testBtn = clone.querySelector('.test-btn');
        if (testBtn) {
            testBtn.innerHTML = `
                <i class="fas fa-sync-alt loading-spinner" style="display: none;"></i>
                Test Now
            `;
            testBtn.addEventListener('click', () => SystemsManager.testSystem(systemId));
        }

        const editBtn = clone.querySelector('.edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => SystemsManager.editSystem(systemId));
        }

        const deleteBtn = clone.querySelector('.delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => SystemsManager.deleteSystem(systemId));
        }
    }

    static updateSystemStatus(systemId: string, status: boolean) {
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
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = '';
        }
    }

    static showEmptyState() {
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-muted">No systems found. Add a system to get started.</p>
                </div>
            `;
        }
    }

    static showErrorState(error: string) {
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-danger">Error loading systems: ${error}</p>
                </div>
            `;
        }
    }
}
