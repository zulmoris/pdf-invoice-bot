/* ===== events.js — Управление событиями ===== */

const Events = {
    init() {
        // Форма события
        const form = document.getElementById('eventForm');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveFromForm();
        });

        // Прогресс цели (для goalForm, но сюда же не относится)
        document.getElementById('goalProgress').addEventListener('input', (e) => {
            document.getElementById('goalProgressValue').textContent = e.target.value;
        });

        // Удаление
        document.getElementById('deleteEventBtn').addEventListener('click', () => this.deleteCurrent());

        // Закрытие модалок
        document.querySelectorAll('[data-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                const modalId = btn.dataset.close;
                document.getElementById(modalId).classList.remove('active');
            });
        });

        // Клик по оверлею — закрыть
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.classList.remove('active');
            });
        });

        // Быстрое добавление
        document.getElementById('quickAddEvent').addEventListener('click', () => {
            this.openModal(null, Utils.today());
        });

        // Enter — отправить форму
        form.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });

        // Color picker — пресеты
        this._selectedColor = '';
        document.getElementById('colorPickerRow').addEventListener('click', (e) => {
            const swatch = e.target.closest('.color-swatch');
            if (!swatch) return;
            document.querySelectorAll('#colorPickerRow .color-swatch').forEach(s => s.classList.remove('selected'));
            swatch.classList.add('selected');
            this._selectedColor = swatch.dataset.color || '';
        });

        // Color picker — свой цвет через input[type=color]
        const customInput = document.getElementById('eventColorCustom');
        customInput.addEventListener('input', () => {
            this._selectedColor = customInput.value;
            document.querySelectorAll('#colorPickerRow .color-swatch').forEach(s => s.classList.remove('selected'));
            customInput.style.outline = '3px solid var(--primary)';
            customInput.style.outlineOffset = '2px';
        });

        // Completed checkbox — показать/скрыть дату завершения
        document.getElementById('eventCompleted').addEventListener('change', (e) => {
            document.getElementById('completedDateGroup').style.display = e.target.checked ? '' : 'none';
            if (e.target.checked) {
                const dateVal = document.getElementById('eventDate').value;
                document.getElementById('eventCompletedAt').value =
                    document.getElementById('eventCompletedAt').value || dateVal || Utils.today();
            }
        });
    },

    /** Открыть модалку: editId=null — новое событие */
    openModal(editId = null, defaultDate = null, defaultTime = null) {
        const modal = document.getElementById('eventModal');
        const titleEl = document.getElementById('eventModalTitle');
        const deleteBtn = document.getElementById('deleteEventBtn');

        if (editId) {
            titleEl.textContent = 'Редактировать событие';
            deleteBtn.style.display = '';
            this._fillForm(editId);
        } else {
            titleEl.textContent = 'Новое событие';
            deleteBtn.style.display = 'none';
            this._resetForm(defaultDate, defaultTime);
        }

        modal.classList.add('active');
        document.getElementById('eventTitle').focus();
    },

    _resetForm(defaultDate, defaultTime) {
        document.getElementById('eventForm').reset();
        document.getElementById('eventId').value = '';
        document.getElementById('eventDate').value = defaultDate || Utils.today();
        if (defaultTime) document.getElementById('eventTimeStart').value = defaultTime;
        this._selectedColor = '';
        this._updateColorPickerUI('');
        document.getElementById('eventCompleted').checked = false;
        document.getElementById('completedDateGroup').style.display = 'none';
        document.getElementById('eventCompletedAt').value = '';
    },

    _updateColorPickerUI(color) {
        document.querySelectorAll('#colorPickerRow .color-swatch').forEach(s => {
            s.classList.toggle('selected', s.dataset.color === (color || ''));
        });
        const custom = document.getElementById('eventColorCustom');
        custom.style.outline = '';
        custom.style.outlineOffset = '';
        // Если цвет не совпадает ни с одним пресетом — выделить custom
        if (color) {
            const presets = Array.from(document.querySelectorAll('#colorPickerRow .color-swatch'));
            const match = presets.find(s => s.dataset.color === color);
            if (!match) {
                custom.value = color;
                custom.style.outline = '3px solid var(--primary)';
                custom.style.outlineOffset = '2px';
            }
        }
    },

    async _fillForm(eventId) {
        const event = await DB.getEvent(eventId);
        if (!event) return;

        document.getElementById('eventId').value = event.id;
        document.getElementById('eventTitle').value = event.title || '';
        document.getElementById('eventDate').value = event.date || '';
        document.getElementById('eventEndDate').value = event.endDate || '';
        document.getElementById('eventTimeStart').value = event.timeStart || '';
        document.getElementById('eventTimeEnd').value = event.timeEnd || '';
        document.getElementById('eventCategory').value = event.category || 'other';
        document.getElementById('eventPriority').value = event.priority || 'medium';
        document.getElementById('eventRepeat').value = event.repeat || 'none';
        document.getElementById('eventReminder').value = event.reminder || 'none';
        document.getElementById('eventDescription').value = event.description || '';
        this._selectedColor = event.color || '';
        this._updateColorPickerUI(event.color || '');

        // Completed
        const isCompleted = !!event.completed;
        document.getElementById('eventCompleted').checked = isCompleted;
        document.getElementById('completedDateGroup').style.display = isCompleted ? '' : 'none';
        document.getElementById('eventCompletedAt').value = event.completedAt || event.date || '';
    },

    async saveFromForm() {
        const id = document.getElementById('eventId').value;
        const title = document.getElementById('eventTitle').value.trim();
        const date = document.getElementById('eventDate').value;

        if (!title || !date) {
            App.toast('Заполните название и дату', 'error');
            return;
        }

        const event = {
            id: id || Utils.generateId(),
            title,
            date,
            endDate: document.getElementById('eventEndDate').value || null,
            timeStart: document.getElementById('eventTimeStart').value || null,
            timeEnd: document.getElementById('eventTimeEnd').value || null,
            category: document.getElementById('eventCategory').value,
            priority: document.getElementById('eventPriority').value,
            repeat: document.getElementById('eventRepeat').value,
            reminder: document.getElementById('eventReminder').value,
            color: this._selectedColor || null,
            description: document.getElementById('eventDescription').value,
            completed: document.getElementById('eventCompleted').checked || false,
            completedAt: document.getElementById('eventCompleted').checked
                ? (document.getElementById('eventCompletedAt').value || date)
                : null,
            createdAt: id ? (await DB.getEvent(id))?.createdAt : new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        await DB.saveEvent(event);
        document.getElementById('eventModal').classList.remove('active');

        // Запланировать напоминание
        if (event.reminder !== 'none') {
            Notifications.scheduleReminder(event);
        }

        App.toast(id ? 'Событие обновлено' : 'Событие создано', 'success');
        Calendar.refresh();
    },

    async deleteCurrent() {
        const id = document.getElementById('eventId').value;
        if (!id) return;

        if (confirm('Удалить это событие?')) {
            await DB.deleteEvent(id);
            document.getElementById('eventModal').classList.remove('active');
            App.toast('Событие удалено', 'success');
            Calendar.refresh();
        }
    },

    /** Быстрое завершение/отмена из календаря */
    async toggleComplete(eventId) {
        const event = await DB.getEvent(eventId);
        if (!event) return;

        if (event.completed) {
            // Отменить завершение
            event.completed = false;
            event.completedAt = null;
            App.toast('Выполнение отменено', 'info');
        } else {
            // Завершить
            event.completed = true;
            event.completedAt = event.completedAt || event.date || Utils.today();
            App.toast('Событие выполнено ✅', 'success');
        }
        event.updatedAt = new Date().toISOString();
        await DB.saveEvent(event);
        Calendar.refresh();
    }
};
