export class ApiService {
    static async handleResponse(response) {
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Network response was not ok');
        }
        return response.json();
    }

    static async getSystems() {
        const response = await fetch('/api/systems');
        return this.handleResponse(response);
    }

    static async testSystem(systemId) {
        const response = await fetch(`/api/systems/${systemId}/test`, {
            method: 'POST'
        });
        return this.handleResponse(response);
    }

    static async addSystem(system) {
        const response = await fetch('/api/systems', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(system)
        });
        return this.handleResponse(response);
    }

    static async updateSystem(systemId, system) {
        const response = await fetch(`/api/systems/${systemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(system)
        });
        return this.handleResponse(response);
    }

    static async deleteSystem(systemId) {
        const response = await fetch(`/api/systems/${systemId}`, {
            method: 'DELETE'
        });
        return this.handleResponse(response);
    }

    static async importSystems(formData) {
        const response = await fetch('/api/systems/import', {
            method: 'POST',
            body: formData
        });
        return this.handleResponse(response);
    }
}
