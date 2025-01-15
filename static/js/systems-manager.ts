class SystemsManager {
    static async initialize() {
        try {
            UiService.initialize();
            await this.loadSystems();
            this.setupEventListeners();
        } catch (error) {
            console.error('Error initializing SystemsManager:', error);
            UiService.showToast('Error initializing application', 'error');
        }
    }

    private static setupEventListeners() {
        const refreshButton = document.getElementById('refreshButton');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.loadSystems());
        }
    }

    static async loadSystems() {
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

    static async testSystem(systemId: string) {
        try {
            const card = document.querySelector(`[data-system-id="${systemId}"]`);
            if (!card) return;

            const loadingSpinner = card.querySelector('.loading-spinner');
            const testBtn = card.querySelector('.test-btn');
            
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

    static async addSystem(system: Partial<System>) {
        try {
            await ApiService.addSystem(system);
            UiService.showToast('System added successfully', 'success');
            await this.loadSystems();
        } catch (error) {
            console.error('Error adding system:', error);
            UiService.showToast('Error adding system', 'error');
        }
    }

    static async updateSystem(systemId: string, system: Partial<System>) {
        try {
            await ApiService.updateSystem(systemId, system);
            UiService.showToast('System updated successfully', 'success');
            await this.loadSystems();
        } catch (error) {
            console.error('Error updating system:', error);
            UiService.showToast('Error updating system', 'error');
        }
    }

    static async deleteSystem(systemId: string) {
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

    static async importSystems(formData: FormData) {
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
