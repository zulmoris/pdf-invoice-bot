/* ===== sync.js — Синхронизация через Google Sheets + Apps Script ===== */

const Sync = {
    _url: '',
    _token: '',
    _deviceId: '',
    _lastSyncAt: null,
    _syncInterval: null,
    _isSyncing: false,
    _pendingDeletes: [],   // [{type, id}]
    _hasLocalChanges: false,

    async init() {
        // Читаем настройки из IndexedDB
        this._url = await DB.getSetting('syncUrl') || '';
        this._token = await DB.getSetting('syncToken') || '';
        this._deviceId = await DB.getSetting('syncDeviceId') || '';
        this._lastSyncAt = await DB.getSetting('syncLastSyncAt') || null;

        if (!this._deviceId) {
            this._deviceId = Utils.generateId();
            await DB.saveSetting('syncDeviceId', this._deviceId);
        }

        // Обновляем UI
        this._updateStatusUI();

        // Если подключено — запускаем фоновую синхронизацию
        if (this._url) {
            this._startBackgroundSync();
            // При закрытии вкладки — финальный push
            window.addEventListener('beforeunload', () => this.pushChanges());
            // При потере фокуса — pull
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && this._url) {
                    this.pullChanges();
                }
            });
        }

        // Привязка UI
        this._bindUI();
    },

    _bindUI() {
        // Кнопка в sidebar
        document.getElementById('btnSync').addEventListener('click', () => {
            document.getElementById('syncUrl').value = this._url;
            document.getElementById('syncToken').value = this._token;
            document.getElementById('syncDeviceId').textContent = this._deviceId.substring(0, 8) + '...';
            document.getElementById('btnSyncDisconnect').style.display = this._url ? '' : 'none';
            document.getElementById('syncModal').classList.add('active');
        });

        // Подключить
        document.getElementById('btnSyncConnect').addEventListener('click', () => this._connect());

        // Отключить
        document.getElementById('btnSyncDisconnect').addEventListener('click', () => this._disconnect());

        // Закрытие модалки
        document.querySelectorAll('[data-close="syncModal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('syncModal').classList.remove('active');
            });
        });
    },

    async _connect() {
        const url = document.getElementById('syncUrl').value.trim();
        const token = document.getElementById('syncToken').value.trim();

        if (!url) {
            App.toast('Введите URL Web App', 'error');
            return;
        }

        // Проверяем связь
        try {
            this._updateIndicator('syncing');
            const testUrl = url + '?action=ping&token=' + encodeURIComponent(token);
            const resp = await fetch(testUrl, { redirect: 'follow' });
            const data = await resp.json();

            if (data.ok) {
                this._url = url;
                this._token = token;
                await DB.saveSetting('syncUrl', url);
                await DB.saveSetting('syncToken', token);

                document.getElementById('syncModal').classList.remove('active');
                App.toast('Подключено к облаку ☁️', 'success');

                // Первая синхронизация
                this._startBackgroundSync();
                await this.fullSync();

                window.addEventListener('beforeunload', () => this.pushChanges());
                document.addEventListener('visibilitychange', () => {
                    if (!document.hidden && this._url) {
                        this.pullChanges();
                    }
                });
            } else if (data.error === 'invalid_token') {
                App.toast('Неверный токен', 'error');
                this._updateIndicator('error');
            } else {
                App.toast('Ошибка подключения: ' + (data.error || 'неизвестная'), 'error');
                this._updateIndicator('error');
            }
        } catch (err) {
            App.toast('Не удалось подключиться. Проверьте URL.', 'error');
            this._updateIndicator('error');
        }
    },

    async _disconnect() {
        this._url = '';
        this._token = '';
        await DB.saveSetting('syncUrl', '');
        await DB.saveSetting('syncToken', '');
        this._stopBackgroundSync();
        document.getElementById('syncModal').classList.remove('active');
        this._updateStatusUI();
        App.toast('Синхронизация отключена', 'success');
    },

    _startBackgroundSync() {
        this._stopBackgroundSync();
        this._syncInterval = setInterval(() => {
            if (!document.hidden) this.pushChanges();
        }, 5 * 60 * 1000); // каждые 5 минут
    },

    _stopBackgroundSync() {
        if (this._syncInterval) {
            clearInterval(this._syncInterval);
            this._syncInterval = null;
        }
    },

    /* --- Изменения для синхронизации --- */

    markChanged(type) {
        this._hasLocalChanges = true;
    },

    markDeleted(type, id) {
        this._pendingDeletes.push({ type, id });
        this._hasLocalChanges = true;
    },

    /* --- Push: отправка локальных изменений на сервер --- */

    async pushChanges() {
        if (!this._url || this._isSyncing) return;
        if (!this._hasLocalChanges && this._pendingDeletes.length === 0) return;

        this._isSyncing = true;
        this._updateIndicator('syncing');

        try {
            const payload = { _deleted: [...this._pendingDeletes] };

            // Отправляем все данные (сервер сам мержит по updatedAt)
            payload.events = await DB.getAllEvents();
            payload.goals = await DB.getAllGoals();
            payload.notes = await DB.getAllNotes();

            const resp = await fetch(this._url + '?action=sync&token=' + encodeURIComponent(this._token), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                redirect: 'follow'
            });

            const data = await resp.json();

            if (data.ok) {
                // Сохраняем пришедшие с сервера изменения (мерж)
                await this._mergeData(data);
                this._pendingDeletes = [];
                this._hasLocalChanges = false;
                this._lastSyncAt = new Date().toISOString();
                await DB.saveSetting('syncLastSyncAt', this._lastSyncAt);
                this._updateStatusUI();
            }
        } catch (err) {
            console.error('Sync push error:', err);
        } finally {
            this._isSyncing = false;
            this._updateIndicator(this._url ? 'connected' : '');
        }
    },

    /* --- Pull: получение изменений с сервера --- */

    async pullChanges() {
        if (!this._url || this._isSyncing) return;

        this._isSyncing = true;
        this._updateIndicator('syncing');

        try {
            const url = this._url + '?action=getAll&token=' + encodeURIComponent(this._token);
            const resp = await fetch(url, { redirect: 'follow' });
            const data = await resp.json();

            if (data.ok) {
                await this._mergeData(data);
                this._lastSyncAt = new Date().toISOString();
                await DB.saveSetting('syncLastSyncAt', this._lastSyncAt);
                this._updateStatusUI();
            }
        } catch (err) {
            console.error('Sync pull error:', err);
        } finally {
            this._isSyncing = false;
            this._updateIndicator(this._url ? 'connected' : '');
        }
    },

    /* --- Full Sync: push + pull --- */

    async fullSync() {
        await this.pushChanges();
        await this.pullChanges();
        // Обновить все виды
        Calendar.refresh();
        Goals.refresh();
        Notes.refresh();
    },

    /* --- Мерж данных (last-write-wins по updatedAt) --- */

    async _mergeData(serverData) {
        // Мержим события
        if (serverData.events && serverData.events.length > 0) {
            const localEvents = await DB.getAllEvents();
            const localMap = {};
            localEvents.forEach(ev => { localMap[ev.id] = ev; });

            let changed = false;
            for (const server of serverData.events) {
                const local = localMap[server.id];
                if (!local) {
                    // Новая запись с сервера
                    await DB.saveEvent(server);
                    changed = true;
                } else {
                    // Сравниваем updatedAt
                    const serverTime = new Date(server.updatedAt || 0).getTime();
                    const localTime = new Date(local.updatedAt || 0).getTime();
                    if (serverTime > localTime) {
                        await DB.saveEvent(server);
                        changed = true;
                    }
                }
            }
        }

        // Мержим цели
        if (serverData.goals && serverData.goals.length > 0) {
            const localGoals = await DB.getAllGoals();
            const localMap = {};
            localGoals.forEach(g => { localMap[g.id] = g; });

            for (const server of serverData.goals) {
                const local = localMap[server.id];
                if (!local) {
                    await DB.saveGoal(server);
                } else {
                    const serverTime = new Date(server.updatedAt || 0).getTime();
                    const localTime = new Date(local.updatedAt || 0).getTime();
                    if (serverTime > localTime) {
                        await DB.saveGoal(server);
                    }
                }
            }
        }

        // Мержим заметки
        if (serverData.notes && serverData.notes.length > 0) {
            const localNotes = await DB.getAllNotes();
            const localMap = {};
            localNotes.forEach(n => { localMap[n.id] = n; });

            for (const server of serverData.notes) {
                const local = localMap[server.id];
                if (!local) {
                    await DB.saveNote(server);
                } else {
                    const serverTime = new Date(server.updatedAt || 0).getTime();
                    const localTime = new Date(local.updatedAt || 0).getTime();
                    if (serverTime > localTime) {
                        await DB.saveNote(server);
                    }
                }
            }
        }
    },

    /* --- UI обновление --- */

    _updateStatusUI() {
        const indicator = document.getElementById('syncIndicator');
        const statusText = document.getElementById('syncStatusText');
        const lastTime = document.getElementById('syncLastTime');

        if (!indicator) return;

        if (this._url) {
            indicator.className = 'sync-indicator connected';
            statusText.textContent = 'Подключено';
            if (this._lastSyncAt) {
                const d = new Date(this._lastSyncAt);
                lastTime.textContent = 'Последняя: ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            } else {
                lastTime.textContent = '';
            }
        } else {
            indicator.className = 'sync-indicator';
            statusText.textContent = 'Не подключено';
            lastTime.textContent = '';
        }
    },

    _updateIndicator(state) {
        const indicator = document.getElementById('syncIndicator');
        if (!indicator) return;
        indicator.className = 'sync-indicator' + (state ? ' ' + state : '');
    }
};
