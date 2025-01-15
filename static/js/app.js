import { SystemsManager } from './modules/systems-manager.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the application
    SystemsManager.initialize().catch(error => {
        console.error('Failed to initialize application:', error);
    });

    // Setup form handlers
    const addSystemForm = document.getElementById('addSystemForm');
    const editSystemForm = document.getElementById('editSystemForm');
    const importForm = document.getElementById('importForm');

    if (addSystemForm) {
        addSystemForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addSystemForm);
            const system = Object.fromEntries(formData.entries());
            
            // Handle cluster nodes and shutdown sequence
            if (system.cluster_nodes) {
                system.cluster_nodes = system.cluster_nodes.split(';')
                    .filter(node => node.trim())
                    .map(host => ({ host: host.trim(), status: false }));
            }
            
            if (system.shutdown_sequence) {
                system.shutdown_sequence = system.shutdown_sequence.split(';')
                    .filter(step => step.trim());
            }

            await SystemsManager.addSystem(system);
            addSystemForm.reset();
            bootstrap.Modal.getInstance(document.getElementById('addModal')).hide();
        });
    }

    if (editSystemForm) {
        editSystemForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(editSystemForm);
            const system = Object.fromEntries(formData.entries());
            const systemId = editSystemForm.dataset.systemId;
            
            // Handle cluster nodes and shutdown sequence
            if (system.cluster_nodes) {
                system.cluster_nodes = system.cluster_nodes.split(';')
                    .filter(node => node.trim())
                    .map(host => ({ host: host.trim(), status: false }));
            }
            
            if (system.shutdown_sequence) {
                system.shutdown_sequence = system.shutdown_sequence.split(';')
                    .filter(step => step.trim());
            }

            await SystemsManager.updateSystem(systemId, system);
            editSystemForm.reset();
            bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
        });
    }

    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(importForm);
            await SystemsManager.importSystems(formData);
            importForm.reset();
            bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
        });
    }
});
