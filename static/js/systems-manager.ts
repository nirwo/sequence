class SystemsManager {
    static async initialize(): Promise<void> {
        try {
            if (!UiService.initialize()) {
                throw new Error('Failed to initialize UI Service');
            }
            await this.loadSystems();
            this.setupEventListeners();
        } catch (error) {
            console.error('Error initializing SystemsManager:', error);
            UiService.showToast('Error initializing application', 'error');
        }
    }

    private static setupEventListeners(): void {
        const refreshButton = document.getElementById('refreshButton');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.loadSystems());
        }
    }

    static async loadSystems(): Promise<void> {
        try {
            UiService.clearSystemsContainer();
            const systems = await ApiService.getSystems();
            
            if (!systems.length) {
                UiService.showEmptyState();
                return;
            }

            const fragment = document.createDocumentFragment();
            systems.forEach(system => {
                const card = UiService.createSystemCard(system);
                if (card) {
                    fragment.appendChild(card);
                }
            });

            const container = document.getElementById('systemsContainer');
            if (container) {
                container.appendChild(fragment);
            }
        } catch (error) {
            console.error('Error loading systems:', error);
            UiService.showToast('Error loading systems', 'error');
            UiService.showErrorState(error instanceof Error ? error.message : 'Unknown error');
        }
    }

    static async testSystem(systemId: string): Promise<void> {
        try {
            const card = document.querySelector(`[data-system-id="${systemId}"]`);
            if (!card) return;

            const loadingSpinner = card.querySelector('.loading-spinner') as HTMLElement;
            const testBtn = card.querySelector('.test-btn') as HTMLButtonElement;
            
            if (loadingSpinner && testBtn) {
                loadingSpinner.style.display = 'inline-block';
                testBtn.innerHTML = `
                    <i class="fas fa-sync-alt loading-spinner" style="display: inline-block;"></i>
                    Testing...
                `;
            }

            const result = await ApiService.testSystem(systemId);
            UiService.updateSystemStatus(systemId, result.status);

            if (result.errors && Object.keys(result.errors).length > 0) {
                let errorMessage = '<ul class="list-unstyled mb-0">';
                for (const [type, error] of Object.entries(result.errors)) {
                    errorMessage += `<li><strong>${type}:</strong> ${error}</li>`;
                }
                errorMessage += '</ul>';
                UiService.showToast(errorMessage, 'error');
            }
        } catch (error) {
            console.error('Error testing system:', error);
            UiService.showToast('Error testing system', 'error');
            UiService.updateSystemStatus(systemId, false);
        }
    }

    static async editSystem(systemId: string): Promise<void> {
        try {
            const systems = await ApiService.getSystems();
            const system = systems.find(s => s._id === systemId);
            
            if (!system) {
                UiService.showToast('System not found', 'error');
                return;
            }

            const form = document.getElementById('editSystemForm') as HTMLFormElement;
            if (!form) {
                UiService.showToast('Edit form not found', 'error');
                return;
            }

            form.dataset.systemId = systemId;
            
            const fields: Record<string, string | undefined> = {
                'name': system.name,
                'app_name': system.app_name,
                'check_type': system.check_type,
                'target': system.target,
                'db_name': system.db_name,
                'db_type': system.db_type,
                'owner': system.owner,
                'shutdown_sequence': system.shutdown_sequence?.join(';'),
                'cluster_nodes': system.cluster_nodes?.map(node => node.host).join(';')
            };

            Object.entries(fields).forEach(([field, value]) => {
                const element = form.querySelector(`[name="${field}"]`) as HTMLInputElement;
                if (element) {
                    element.value = value || '';
                }
            });

            const modal = new bootstrap.Modal(document.getElementById('editModal') as HTMLElement);
            modal.show();
        } catch (error) {
            console.error('Error editing system:', error);
            UiService.showToast('Error editing system', 'error');
        }
    }

    static async deleteSystem(systemId: string): Promise<void> {
        if (!confirm('Are you sure you want to delete this system?')) {
            return;
        }

        try {
            await ApiService.deleteSystem(systemId);
            UiService.showToast('System deleted successfully', 'success');
            await this.loadSystems();
        } catch (error) {
            console.error('Error deleting system:', error);
            UiService.showToast('Error deleting system', 'error');
        }
    }

    static async addSystem(system: Partial<System>): Promise<void> {
        try {
            await ApiService.addSystem(system);
            UiService.showToast('System added successfully', 'success');
            await this.loadSystems();
        } catch (error) {
            console.error('Error adding system:', error);
            UiService.showToast('Error adding system', 'error');
        }
    }

    static async updateSystem(systemId: string, system: Partial<System>): Promise<void> {
        try {
            await ApiService.updateSystem(systemId, system);
            UiService.showToast('System updated successfully', 'success');
            await this.loadSystems();
        } catch (error) {
            console.error('Error updating system:', error);
            UiService.showToast('Error updating system', 'error');
        }
    }

    static async importSystems(formData: FormData): Promise<void> {
        try {
            const result = await ApiService.importSystems(formData);
            UiService.showToast(result.message, 'success');
            
            if (result.warnings?.length) {
                result.warnings.forEach(warning => {
                    UiService.showToast(warning, 'error');
                });
            }
            
            await this.loadSystems();
        } catch (error) {
            console.error('Error importing systems:', error);
            UiService.showToast('Error importing systems', 'error');
        }
    }
}
