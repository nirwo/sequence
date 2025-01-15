class UiService {
    private static systemCardTemplate: HTMLTemplateElement | null = null;
    private static systemsContainer: HTMLElement | null = null;
    private static toastContainer: HTMLDivElement | null = null;
    private static initialized: boolean = false;

    static initialize(): boolean {
        if (this.initialized) {
            return true;
        }

        try {
            this.systemCardTemplate = document.getElementById('systemCardTemplate') as HTMLTemplateElement;
            this.systemsContainer = document.getElementById('systemsContainer') as HTMLDivElement;
            
            if (!this.systemCardTemplate || !this.systemsContainer) {
                console.error('Required DOM elements not found. Make sure the page is fully loaded.');
                return false;
            }

            this.ensureToastContainer();
            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Error initializing UI Service:', error);
            return false;
        }
    }

    private static ensureToastContainer(): void {
        if (this.toastContainer) {
            return;
        }

        let container = document.getElementById('toastContainer') as HTMLDivElement;
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        this.toastContainer = container;
    }

    static showToast(message: string, type: 'success' | 'error' = 'success', duration = 5000): void {
        this.ensureToastContainer();
        if (!this.toastContainer) return;

        const toast = document.createElement('div') as HTMLDivElement;
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
            if (this.toastContainer && this.toastContainer.children.length === 0) {
                this.toastContainer.remove();
                this.toastContainer = null;
            }
        });
    }

    static createSystemCard(system: System): DocumentFragment | null {
        if (!this.systemCardTemplate) return null;

        try {
            const clone = document.importNode(this.systemCardTemplate.content, true);
            const card = clone.querySelector('.card') as HTMLDivElement;
            if (!card) return null;

            card.setAttribute('data-system-id', system._id);

            // Set system name and status
            const elements: Record<string, string> = {
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

            this.setupClusterNodes(clone, system);
            this.setupButtons(clone, system._id);

            return clone;
        } catch (error) {
            console.error('Error creating system card:', error);
            return null;
        }
    }

    private static setupClusterNodes(clone: DocumentFragment, system: System): void {
        const clusterNodesDiv = clone.querySelector('.cluster-nodes') as HTMLDivElement;
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

    private static setupButtons(clone: DocumentFragment, systemId: string): void {
        const testBtn = clone.querySelector('.test-btn') as HTMLButtonElement;
        if (testBtn) {
            testBtn.innerHTML = `
                <i class="fas fa-sync-alt loading-spinner" style="display: none;"></i>
                Test Now
            `;
            testBtn.addEventListener('click', () => SystemsManager.testSystem(systemId));
        }

        const editBtn = clone.querySelector('.edit-btn') as HTMLButtonElement;
        if (editBtn) {
            editBtn.addEventListener('click', () => SystemsManager.editSystem(systemId));
        }

        const deleteBtn = clone.querySelector('.delete-btn') as HTMLButtonElement;
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => SystemsManager.deleteSystem(systemId));
        }
    }

    static updateSystemStatus(systemId: string, status: boolean): void {
        const systemCard = document.querySelector(`[data-system-id="${systemId}"]`) as HTMLElement;
        if (!systemCard) return;

        const elements = {
            statusBadge: systemCard.querySelector('.status-badge') as HTMLElement,
            statusText: systemCard.querySelector('.status-text') as HTMLElement,
            loadingSpinner: systemCard.querySelector('.loading-spinner') as HTMLElement,
            testBtn: systemCard.querySelector('.test-btn') as HTMLButtonElement
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

    static clearSystemsContainer(): void {
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = '';
        }
    }

    static showEmptyState(): void {
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-muted">No systems found. Add a system to get started.</p>
                </div>
            `;
        }
    }

    static showErrorState(error: string): void {
        if (this.systemsContainer) {
            this.systemsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-danger">Error loading systems: ${error}</p>
                </div>
            `;
        }
    }
}
