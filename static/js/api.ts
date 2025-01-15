class ApiService {
    private static async handleResponse<T>(response: Response): Promise<T> {
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Network response was not ok');
        }
        return response.json();
    }

    static async getSystems(): Promise<System[]> {
        const response = await fetch('/api/systems');
        return this.handleResponse<System[]>(response);
    }

    static async testSystem(systemId: string): Promise<{ status: boolean; errors?: Record<string, string> }> {
        const response = await fetch(`/api/systems/${systemId}/test`, {
            method: 'POST'
        });
        return this.handleResponse(response);
    }

    static async addSystem(system: Partial<System>): Promise<System> {
        const response = await fetch('/api/systems', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(system)
        });
        return this.handleResponse(response);
    }

    static async updateSystem(systemId: string, system: Partial<System>): Promise<System> {
        const response = await fetch(`/api/systems/${systemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(system)
        });
        return this.handleResponse(response);
    }

    static async deleteSystem(systemId: string): Promise<void> {
        const response = await fetch(`/api/systems/${systemId}`, {
            method: 'DELETE'
        });
        return this.handleResponse(response);
    }

    static async importSystems(formData: FormData): Promise<{ message: string; warnings?: string[] }> {
        const response = await fetch('/api/systems/import', {
            method: 'POST',
            body: formData
        });
        return this.handleResponse(response);
    }
}
