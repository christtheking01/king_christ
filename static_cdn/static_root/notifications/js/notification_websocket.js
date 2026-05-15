/**
 * Live Notification WebSocket Client
 * Handles real-time notification updates via WebSocket
 */

class NotificationWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.messageHandlers = [];
        
        this.init();
    }
    
    init() {
        // Check if user is authenticated (only connect for logged-in users)
        if (!document.body.dataset.userAuthenticated) {
            console.log('User not authenticated, skipping WebSocket connection');
            return;
        }
        
        this.connect();
        this.setupUIListeners();
    }
    
    connect() {
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/notifications/`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (event) => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.onConnectionEstablished();
            };
            
            this.socket.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.socket.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                this.attemptReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.attemptReconnect();
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.log('Max reconnection attempts reached');
            this.fallbackToPolling();
        }
    }
    
    fallbackToPolling() {
        console.log('Falling back to polling for notifications');
        // Poll every 30 seconds as fallback
        setInterval(() => this.fetchNotifications(), 30000);
    }
    
    handleMessage(data) {
        console.log('WebSocket message received:', data);
        
        switch (data.type) {
            case 'initial_count':
                this.updateBadge(data.unread_count);
                break;
                
            case 'new_notification':
                this.handleNewNotification(data.notification);
                this.updateBadge(data.unread_count);
                this.showNotificationToast(data.notification);
                break;
                
            case 'unread_count_updated':
                this.updateBadge(data.unread_count);
                break;
                
            case 'unread_notifications':
                this.updateNotificationList(data.notifications);
                break;
                
            case 'error':
                console.error('Notification error:', data.message);
                break;
        }
        
        // Call registered handlers
        this.messageHandlers.forEach(handler => handler(data));
    }
    
    handleNewNotification(notification) {
        // Add to notification dropdown if present
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
            const newItem = this.createNotificationItem(notification);
            notificationList.insertBefore(newItem, notificationList.firstChild);
            
            // Remove empty state if present
            const emptyState = notificationList.querySelector('.text-center');
            if (emptyState) {
                emptyState.remove();
            }
            
            // Keep only top 10 in dropdown
            const items = notificationList.querySelectorAll('.notification-item');
            if (items.length > 10) {
                for (let i = 10; i < items.length; i++) {
                    items[i].remove();
                }
            }
        }
        
        // Play sound for high/urgent priority
        if (notification.priority === 'high' || notification.priority === 'urgent') {
            this.playNotificationSound();
        }
    }
    
    createNotificationItem(notification) {
        const div = document.createElement('a');
        div.href = `/notifications/my/${notification.id}/`;
        div.className = 'dropdown-item notification-item p-3 border-bottom';
        
        if (notification.priority === 'urgent') {
            div.classList.add('bg-danger', 'bg-opacity-10');
        } else if (notification.priority === 'high') {
            div.classList.add('bg-warning', 'bg-opacity-10');
        }
        
        const iconBg = notification.priority === 'urgent' ? '#dc3545' : 
                      notification.priority === 'high' ? '#ffc107' : 
                      notification.priority === 'low' ? '#6c757d' : '#0d6efd';
        
        div.innerHTML = `
            <div class="d-flex gap-3">
                <div class="flex-shrink-0">
                    <div class="notification-icon rounded-circle d-flex align-items-center justify-content-center" 
                         style="width: 40px; height: 40px; background: ${iconBg}; color: white;">
                        <i class="fas fa-bell"></i>
                    </div>
                </div>
                <div class="flex-grow-1 min-width-0">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <h6 class="mb-0 text-truncate fw-semibold" style="max-width: 200px;">${this.escapeHtml(notification.title)}</h6>
                        <small class="text-muted flex-shrink-0 ms-2">Just now</small>
                    </div>
                    <p class="mb-0 text-truncate text-muted" style="font-size: 0.875rem;">${this.escapeHtml(notification.message.substring(0, 50))}...</p>
                    <div class="mt-1">
                        ${notification.priority === 'urgent' ? '<span class="badge bg-danger">Urgent</span>' : ''}
                        ${notification.priority === 'high' ? '<span class="badge bg-warning text-dark">High</span>' : ''}
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    updateBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.toggle('d-none', count === 0);
            
            // Add pulse animation
            badge.classList.add('notification-badge-pulse');
            setTimeout(() => badge.classList.remove('notification-badge-pulse'), 500);
        }
        
        // Update page title with unread count
        if (count > 0) {
            document.title = `(${count}) ${document.title.replace(/^\(\d+\)\s*/, '')}`;
        } else {
            document.title = document.title.replace(/^\(\d+\)\s*/, '');
        }
    }
    
    updateNotificationList(notifications) {
        const list = document.getElementById('notification-list');
        if (list && notifications.length === 0) {
            list.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p class="mb-0">No new notifications</p>
                </div>
            `;
        }
    }
    
    showNotificationToast(notification) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const bgClass = notification.priority === 'urgent' ? 'bg-danger' : 
                       notification.priority === 'high' ? 'bg-warning' : 'bg-primary';
        
        toast.innerHTML = `
            <div class="d-flex ${bgClass} text-white">
                <div class="toast-body">
                    <strong><i class="fas fa-bell me-2"></i>${this.escapeHtml(notification.title)}</strong>
                    <p class="mb-0 mt-1">${this.escapeHtml(notification.message.substring(0, 100))}</p>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add to toast container
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();
        
        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
    
    playNotificationSound() {
        // Create and play notification sound
        const audio = new Audio('/static/notifications/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => {
            // Audio autoplay may be blocked
            console.log('Audio play blocked:', e);
        });
    }
    
    setupUIListeners() {
        // Mark all as read button
        const markAllBtn = document.getElementById('markAllReadBtn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => {
                this.send({ action: 'mark_all_read' });
            });
        }
        
        // Mark individual notification as read
        document.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const notificationId = e.target.dataset.notificationId;
                this.send({ action: 'mark_read', notification_id: notificationId });
            });
        });
        
        // Fetch unread notifications button
        const fetchBtn = document.getElementById('fetchUnreadBtn');
        if (fetchBtn) {
            fetchBtn.addEventListener('click', () => {
                this.send({ action: 'fetch_unread' });
            });
        }
    }
    
    onConnectionEstablished() {
        // Request initial unread count
        this.send({ action: 'fetch_unread' });
    }
    
    send(data) {
        if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.log('WebSocket not connected, using HTTP fallback');
            this.httpFallback(data);
        }
    }
    
    httpFallback(data) {
        // Fallback to HTTP API when WebSocket is not available
        if (data.action === 'mark_all_read') {
            fetch('/notifications/api/my/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                },
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    this.updateBadge(0);
                }
            });
        } else if (data.action === 'mark_read' && data.notification_id) {
            fetch(`/notifications/api/my/${data.notification_id}/mark-read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                },
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    this.updateBadge(result.unread_count);
                }
            });
        }
    }
    
    fetchNotifications() {
        // HTTP polling fallback
        fetch('/notifications/api/my/')
            .then(response => response.json())
            .then(data => {
                this.updateBadge(data.unread_count);
            })
            .catch(error => console.error('Error fetching notifications:', error));
    }
    
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Public method to register custom message handlers
    onMessage(handler) {
        this.messageHandlers.push(handler);
    }
    
    // Public method to disconnect
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.notificationWS = new NotificationWebSocket();
    });
} else {
    window.notificationWS = new NotificationWebSocket();
}
