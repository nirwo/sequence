interface ClusterNode {
    host: string;
    status: boolean;
    last_check?: Date;
    http_status?: boolean;
    http_error?: string;
    ping_status?: boolean;
    ping_error?: string;
}

interface System {
    _id: string;
    name: string;
    app_name?: string;
    check_type: 'ping' | 'http' | 'both';
    target?: string;
    db_name?: string;
    db_type?: string;
    db_port?: number;
    owner?: string;
    mount_points?: string[];
    shutdown_sequence?: string[];
    cluster_nodes?: ClusterNode[];
    created_at: Date;
    last_check?: Date;
    status: boolean;
    sequence_status: 'not_started' | 'in_progress' | 'completed' | 'failed';
    http_status?: boolean;
    http_error?: string;
    ping_status?: boolean;
    ping_error?: string;
    db_status?: boolean;
    last_error?: string;
}
