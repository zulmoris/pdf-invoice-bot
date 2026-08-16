/* ===== notes.js — Управление заметками ===== */

const Notes = {
    init() {
        document.getElementById('addNoteBtn').addEventListener('click', () => {
            this.openModal();
        });

        document.getElementById('noteForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveFromForm();
        });

        document.getElementById('deleteNoteBtn').addEventListener('click', () => this.deleteCurrent());
    },

    async refresh() {
        const notes = await DB.getAllNotes();
        this.render(notes);
    },

    render(notes) {
        const container = document.getElementById('notesContainer');

        if (!notes || notes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📓</div>
                    <div class="empty-text">Заметок пока нет. Создайте первую!</div>
                </div>`;
            return;
        }

        // Сортировка: с датой сверху, потом по дате обновления
        const sorted = [...notes].sort((a, b) => {
            // С привязанной датой — сверху
            if (a.date && !b.date) return -1;
            if (!a.date && b.date) return 1;
            if (a.date && b.date) return b.date.localeCompare(a.date);
            return (b.updatedAt || '').localeCompare(a.updatedAt || '');
        });

        container.innerHTML = sorted.map(note => {
            const cat = note.category ? CATEGORIES[note.category] : null;
            return `
            <div class="note-card" data-note-id="${note.id}">
                <div class="note-card-title">${Utils.escapeHtml(note.title)}</div>
                <div class="note-card-content">${Utils.escapeHtml(note.content)}</div>
                <div class="note-card-meta">
                    ${note.date ? `<span>📅 ${Utils.formatDateRu(note.date)}</span>` : ''}
                    ${cat ? `<span>${cat.emoji} ${cat.label}</span>` : ''}
                </div>
            </div>`;
        }).join('');

        // Клик — редактирование
        container.querySelectorAll('.note-card').forEach(card => {
            card.addEventListener('click', () => {
                this.openModal(card.dataset.noteId);
            });
        });
    },

    openModal(editId = null) {
        const modal = document.getElementById('noteModal');
        const titleEl = document.getElementById('noteModalTitle');
        const deleteBtn = document.getElementById('deleteNoteBtn');

        if (editId) {
            titleEl.textContent = 'Редактировать заметку';
            deleteBtn.style.display = '';
            this._fillForm(editId);
        } else {
            titleEl.textContent = 'Новая заметка';
            deleteBtn.style.display = 'none';
            this._resetForm();
        }

        modal.classList.add('active');
        document.getElementById('noteTitle').focus();
    },

    _resetForm() {
        document.getElementById('noteForm').reset();
        document.getElementById('noteId').value = '';
    },

    async _fillForm(noteId) {
        const note = await DB.getNote(noteId);
        if (!note) return;

        document.getElementById('noteId').value = note.id;
        document.getElementById('noteTitle').value = note.title || '';
        document.getElementById('noteDate').value = note.date || '';
        document.getElementById('noteCategory').value = note.category || '';
        document.getElementById('noteContent').value = note.content || '';
    },

    async saveFromForm() {
        const id = document.getElementById('noteId').value;
        const title = document.getElementById('noteTitle').value.trim();

        if (!title) {
            App.toast('Введите заголовок заметки', 'error');
            return;
        }

        const note = {
            id: id || Utils.generateId(),
            title,
            date: document.getElementById('noteDate').value || null,
            category: document.getElementById('noteCategory').value || null,
            content: document.getElementById('noteContent').value,
            createdAt: id ? (await DB.getNote(id))?.createdAt : new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        await DB.saveNote(note);
        document.getElementById('noteModal').classList.remove('active');
        App.toast(id ? 'Заметка обновлена' : 'Заметка создана', 'success');
        this.refresh();
    },

    async deleteCurrent() {
        const id = document.getElementById('noteId').value;
        if (!id) return;

        if (confirm('Удалить эту заметку?')) {
            await DB.deleteNote(id);
            document.getElementById('noteModal').classList.remove('active');
            App.toast('Заметка удалена', 'success');
            this.refresh();
        }
    }
};
