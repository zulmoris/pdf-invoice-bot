/* ===== db.js — IndexedDB Database ===== */

const DB = {
    name: 'PlannerDB',
    version: 1,
    db: null,

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.name, this.version);

            request.onupgradeneeded = (e) => {
                const db = e.target.result;

                // События
                if (!db.objectStoreNames.contains('events')) {
                    const eventsStore = db.createObjectStore('events', { keyPath: 'id' });
                    eventsStore.createIndex('date', 'date', { unique: false });
                    eventsStore.createIndex('category', 'category', { unique: false });
                    eventsStore.createIndex('repeat', 'repeat', { unique: false });
                }

                // Цели
                if (!db.objectStoreNames.contains('goals')) {
                    const goalsStore = db.createObjectStore('goals', { keyPath: 'id' });
                    goalsStore.createIndex('status', 'status', { unique: false });
                    goalsStore.createIndex('category', 'category', { unique: false });
                }

                // Заметки
                if (!db.objectStoreNames.contains('notes')) {
                    const notesStore = db.createObjectStore('notes', { keyPath: 'id' });
                    notesStore.createIndex('date', 'date', { unique: false });
                    notesStore.createIndex('category', 'category', { unique: false });
                }

                // Настройки
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'key' });
                }
            };

            request.onsuccess = (e) => {
                this.db = e.target.result;
                resolve(this.db);
            };

            request.onerror = (e) => {
                reject(e.target.error);
            };
        });
    },

    _tx(storeName, mode = 'readonly') {
        const tx = this.db.transaction(storeName, mode);
        return tx.objectStore(storeName);
    },

    _wrap(request) {
        return new Promise((resolve, reject) => {
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    // --- Events ---
    async getAllEvents() {
        return this._wrap(this._tx('events').getAll());
    },

    async getEvent(id) {
        return this._wrap(this._tx('events').get(id));
    },

    async saveEvent(event) {
        return this._wrap(this._tx('events', 'readwrite').put(event));
    },

    async deleteEvent(id) {
        return this._wrap(this._tx('events', 'readwrite').delete(id));
    },

    async getEventsByDate(dateStr) {
        const all = await this.getAllEvents();
        return all.filter(ev => Utils.isEventOnDate(ev, dateStr));
    },

    async getEventsByDateRange(startDate, endDate) {
        const all = await this.getAllEvents();
        return all.filter(ev => {
            // Проверяем, есть ли хотя бы одно вхождение события в диапазоне
            for (let d = startDate; d <= endDate; d = Utils.addDays(d, 1)) {
                if (Utils.isEventOnDate(ev, d)) return true;
            }
            return false;
        });
    },

    // --- Goals ---
    async getAllGoals() {
        return this._wrap(this._tx('goals').getAll());
    },

    async getGoal(id) {
        return this._wrap(this._tx('goals').get(id));
    },

    async saveGoal(goal) {
        return this._wrap(this._tx('goals', 'readwrite').put(goal));
    },

    async deleteGoal(id) {
        return this._wrap(this._tx('goals', 'readwrite').delete(id));
    },

    // --- Notes ---
    async getAllNotes() {
        return this._wrap(this._tx('notes').getAll());
    },

    async getNote(id) {
        return this._wrap(this._tx('notes').get(id));
    },

    async saveNote(note) {
        return this._wrap(this._tx('notes', 'readwrite').put(note));
    },

    async deleteNote(id) {
        return this._wrap(this._tx('notes', 'readwrite').delete(id));
    },

    // --- Settings ---
    async getSetting(key) {
        const result = await this._wrap(this._tx('settings').get(key));
        return result ? result.value : null;
    },

    async saveSetting(key, value) {
        return this._wrap(this._tx('settings', 'readwrite').put({ key, value }));
    },

    // --- Export / Import ---
    async exportAll() {
        const events = await this.getAllEvents();
        const goals = await this.getAllGoals();
        const notes = await this.getAllNotes();
        return {
            version: 1,
            exportedAt: new Date().toISOString(),
            events,
            goals,
            notes
        };
    },

    async importAll(data) {
        if (!data || !data.events) throw new Error('Неверный формат файла');

        const tx = this.db.transaction(['events', 'goals', 'notes'], 'readwrite');

        // Очистить текущие данные
        tx.objectStore('events').clear();
        tx.objectStore('goals').clear();
        tx.objectStore('notes').clear();

        // Добавить импортированные
        for (const event of data.events) {
            tx.objectStore('events').put(event);
        }
        for (const goal of (data.goals || [])) {
            tx.objectStore('goals').put(goal);
        }
        for (const note of (data.notes || [])) {
            tx.objectStore('notes').put(note);
        }

        return new Promise((resolve, reject) => {
            tx.oncomplete = () => {
                if (typeof Sync !== 'undefined') Sync.markChanged('import');
                resolve();
            };
            tx.onerror = () => reject(tx.error);
        });
    }
};

/* ===== Хуки синхронизации — перехват записи/удаления ===== */
(function hookSync() {
    function defer(fn) {
        // Sync может быть ещё не загружен — откладываем до init
        const origInit = DB.init.bind(DB);
        DB.init = async function() {
            const result = await origInit();
            if (typeof Sync !== 'undefined') fn();
            return result;
        };
        // А если уже загружен — вызовем сразу
        setTimeout(() => { if (typeof Sync !== 'undefined') fn(); }, 0);
    }

    const _origSaveEvent = DB.saveEvent.bind(DB);
    DB.saveEvent = async function(event) {
        await _origSaveEvent(event);
        if (typeof Sync !== 'undefined') Sync.markChanged('event');
    };

    const _origDeleteEvent = DB.deleteEvent.bind(DB);
    DB.deleteEvent = async function(id) {
        await _origDeleteEvent(id);
        if (typeof Sync !== 'undefined') Sync.markDeleted('event', id);
    };

    const _origSaveGoal = DB.saveGoal.bind(DB);
    DB.saveGoal = async function(goal) {
        await _origSaveGoal(goal);
        if (typeof Sync !== 'undefined') Sync.markChanged('goal');
    };

    const _origDeleteGoal = DB.deleteGoal.bind(DB);
    DB.deleteGoal = async function(id) {
        await _origDeleteGoal(id);
        if (typeof Sync !== 'undefined') Sync.markDeleted('goal', id);
    };

    const _origSaveNote = DB.saveNote.bind(DB);
    DB.saveNote = async function(note) {
        await _origSaveNote(note);
        if (typeof Sync !== 'undefined') Sync.markChanged('note');
    };

    const _origDeleteNote = DB.deleteNote.bind(DB);
    DB.deleteNote = async function(id) {
        await _origDeleteNote(id);
        if (typeof Sync !== 'undefined') Sync.markDeleted('note', id);
    };
})();
