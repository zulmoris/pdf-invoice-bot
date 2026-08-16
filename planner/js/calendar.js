/* ===== calendar.js — Рендер календаря ===== */

const Calendar = {
    currentDate: new Date(),    // Текущая дата для навигации
    selectedDate: null,         // Выбранная дата (YYYY-MM-DD)
    viewMode: 'month',          // month | week | day
    allEvents: [],               // Кэш всех событий
    container: null,

    init() {
        this.container = document.getElementById('calendarContainer');
        this.selectedDate = Utils.today();
        this.refresh();
    },

    async refresh() {
        this.allEvents = await DB.getAllEvents();
        this.render();
        this.updateNavLabel();
    },

    updateNavLabel() {
        const label = document.getElementById('navLabel');
        const d = this.currentDate;

        if (this.viewMode === 'month') {
            label.textContent = Utils.formatMonthYear(d);
        } else if (this.viewMode === 'week') {
            const dates = Utils.getWeekDates(d);
            label.textContent = `${Utils.formatDateRu(dates[0])} — ${Utils.formatDateRu(dates[6])}`;
        } else {
            label.textContent = Utils.formatDateFullRu(Utils.formatDate(d));
        }
    },

    setViewMode(mode) {
        this.viewMode = mode;

        // Обновить кнопки
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.viewmode === mode);
        });

        // Показать/скрыть навигацию
        const calNav = document.getElementById('calendarNav');
        calNav.style.display = '';

        this.refresh();
    },

    navigate(direction) {
        const d = this.currentDate;
        if (this.viewMode === 'month') {
            d.setMonth(d.getMonth() + direction);
        } else if (this.viewMode === 'week') {
            d.setDate(d.getDate() + direction * 7);
        } else {
            d.setDate(d.getDate() + direction);
        }
        this.refresh();
    },

    goToToday() {
        this.currentDate = new Date();
        this.selectedDate = Utils.today();
        this.refresh();
    },

    goToDate(dateStr) {
        this.currentDate = Utils.parseDate(dateStr);
        this.selectedDate = dateStr;
        this.refresh();
    },

    render() {
        switch (this.viewMode) {
            case 'month': this.renderMonth(); break;
            case 'week':  this.renderWeek();  break;
            case 'day':   this.renderDay();   break;
        }
    },

    // --- Month View ---
    renderMonth() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startWeekday = (firstDay.getDay() + 6) % 7; // Пн=0

        const today = Utils.today();
        let html = '<div class="month-header">';
        WEEKDAYS_RU_SHORT.forEach(d => {
            html += `<div class="month-header-cell">${d}</div>`;
        });
        html += '</div><div class="month-grid">';

        // Дни предыдущего месяца
        const prevMonthLast = new Date(year, month, 0);
        for (let i = startWeekday - 1; i >= 0; i--) {
            const day = prevMonthLast.getDate() - i;
            const dateStr = Utils.formatDate(new Date(year, month - 1, day));
            html += this._renderMonthDay(dateStr, day, true, today);
        }

        // Дни текущего месяца
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const dateStr = Utils.formatDate(new Date(year, month, day));
            html += this._renderMonthDay(dateStr, day, false, today);
        }

        // Дни следующего месяца
        const totalCells = startWeekday + lastDay.getDate();
        const remaining = (7 - (totalCells % 7)) % 7;
        for (let day = 1; day <= remaining; day++) {
            const dateStr = Utils.formatDate(new Date(year, month + 1, day));
            html += this._renderMonthDay(dateStr, day, true, today);
        }

        html += '</div>';
        this.container.innerHTML = html;
        this._bindMonthClicks();
    },

    _renderMonthDay(dateStr, day, isOtherMonth, today) {
        const isToday = dateStr === today;
        const isSelected = dateStr === this.selectedDate;
        const classes = ['month-day'];
        if (isOtherMonth) classes.push('other-month');
        if (isToday) classes.push('today');
        if (isSelected) classes.push('selected');

        const events = this.allEvents.filter(ev => Utils.isEventOnDate(ev, dateStr));
        const maxShow = 3;

        let html = `<div class="${classes.join(' ')}" data-date="${dateStr}">`;
        html += `<div class="day-number">${day}</div>`;
        html += '<div class="events-list">';

        events.slice(0, maxShow).forEach(ev => {
            const colorStyle = ev.color ? `style="background-color:${ev.color};color:#fff"` : '';
            const completedClass = ev.completed ? ' event-completed' : '';
            const checkMark = ev.completed ? '✓ ' : '';
            html += `<div class="month-event event-cat-${ev.category}${completedClass}" data-event-id="${ev.id}" ${colorStyle} title="${Utils.escapeHtml(ev.title)}${ev.completed ? ' (выполнено)' : ''}">`;
            if (ev.timeStart) html += ev.timeStart + ' ';
            html += checkMark + Utils.escapeHtml(ev.title);
            html += '</div>';
        });

        if (events.length > maxShow) {
            html += `<div class="month-event-more">ещё ${events.length - maxShow}</div>`;
        }

        html += '</div></div>';
        return html;
    },

    _bindMonthClicks() {
        // Клик по дню
        this.container.querySelectorAll('.month-day').forEach(cell => {
            cell.addEventListener('click', (e) => {
                // Если кликнули на чекмарк завершения
                const checkEl = e.target.closest('.event-check-btn');
                if (checkEl) {
                    e.stopPropagation();
                    Events.toggleComplete(checkEl.dataset.eventId);
                    return;
                }
                // Если кликнули на событие — открыть его
                const eventEl = e.target.closest('.month-event');
                if (eventEl) {
                    Events.openModal(eventEl.dataset.eventId);
                    return;
                }
                // Иначе — выбрать день
                this.selectedDate = cell.dataset.date;
                this.refresh();
            });

            // Двойной клик — быстрое создание события
            cell.addEventListener('dblclick', () => {
                Events.openModal(null, cell.dataset.date);
            });
        });
    },

    // --- Week View ---
    renderWeek() {
        const dates = Utils.getWeekDates(this.currentDate);
        const today = Utils.today();
        const hours = [];
        for (let h = 0; h < 24; h++) {
            hours.push(String(h).padStart(2, '0') + ':00');
        }

        let html = '<div class="week-header">';
        html += '<div class="week-header-cell"></div>';
        dates.forEach(dateStr => {
            const d = Utils.parseDate(dateStr);
            const isToday = dateStr === today;
            const wd = Utils.getWeekday(dateStr);
            html += `<div class="week-header-cell ${isToday ? 'today' : ''}">`;
            html += `${WEEKDAYS_RU_SHORT[wd]}`;
            html += `<span class="day-num">${d.getDate()}</span>`;
            html += '</div>';
        });
        html += '</div>';

        html += '<div class="week-grid">';
        hours.forEach(hour => {
            html += `<div class="week-time">${hour}</div>`;
            dates.forEach(dateStr => {
                const h = parseInt(hour);
                const events = this.allEvents.filter(ev => {
                    if (!Utils.isEventOnDate(ev, dateStr)) return false;
                    if (!ev.timeStart) return false;
                    const evHour = parseInt(ev.timeStart.split(':')[0]);
                    return evHour === h;
                });

                html += `<div class="week-cell" data-date="${dateStr}" data-hour="${h}">`;
                events.forEach(ev => {
                    const colorStyle = ev.color ? `style="background-color:${ev.color};color:#fff"` : '';
                    const completedClass = ev.completed ? ' event-completed' : '';
                    const checkMark = ev.completed ? '✓ ' : '';
                    html += `<div class="week-event event-cat-${ev.category}${completedClass}" data-event-id="${ev.id}" ${colorStyle}>${checkMark}${Utils.escapeHtml(ev.title)}</div>`;
                });
                html += '</div>';
            });
        });
        html += '</div>';

        this.container.innerHTML = html;
        this._bindWeekClicks();
    },

    _bindWeekClicks() {
        this.container.querySelectorAll('.week-event').forEach(el => {
            el.addEventListener('click', (e) => {
                const checkEl = e.target.closest('.event-check-btn');
                if (checkEl) {
                    e.stopPropagation();
                    Events.toggleComplete(checkEl.dataset.eventId);
                    return;
                }
                e.stopPropagation();
                Events.openModal(el.dataset.eventId);
            });
        });

        this.container.querySelectorAll('.week-cell').forEach(cell => {
            cell.addEventListener('dblclick', () => {
                const date = cell.dataset.date;
                const hour = String(cell.dataset.hour).padStart(2, '0') + ':00';
                Events.openModal(null, date, hour);
            });
        });
    },

    // --- Day View ---
    renderDay() {
        const dateStr = Utils.formatDate(this.currentDate);
        const today = Utils.today();
        const hours = [];
        for (let h = 0; h < 24; h++) {
            hours.push(String(h).padStart(2, '0'));
        }

        // Аллдей события
        const alldayEvents = this.allEvents.filter(ev =>
            Utils.isEventOnDate(ev, dateStr) && !ev.timeStart
        );
        // Таймед события
        const timedEvents = this.allEvents.filter(ev =>
            Utils.isEventOnDate(ev, dateStr) && ev.timeStart
        );

        let html = '<div class="day-view">';
        html += '<div class="day-header">';
        html += `<div class="day-title">${Utils.formatDateFullRu(dateStr)}</div>`;
        if (dateStr === today) html += '<div class="day-subtitle">Сегодня</div>';
        html += '</div>';

        // Аллдей
        html += '<div class="day-allday-events">';
        if (alldayEvents.length) {
            alldayEvents.forEach(ev => {
                const colorStyle = ev.color ? `style="background-color:${ev.color};color:#fff"` : '';
                const completedClass = ev.completed ? ' event-completed' : '';
                const checkMark = ev.completed ? '✓ ' : '';
                html += `<div class="day-allday-event event-cat-${ev.category}${completedClass}" data-event-id="${ev.id}" ${colorStyle}>${checkMark}${Utils.escapeHtml(ev.title)}</div>`;
            });
        }
        html += '</div>';

        // Таймлайн
        html += '<div class="day-timeline">';
        hours.forEach(hour => {
            html += `<div class="day-time-label">${hour}:00</div>`;
            const h = parseInt(hour);
            const slotEvents = timedEvents.filter(ev => parseInt(ev.timeStart.split(':')[0]) === h);

            html += `<div class="day-slot" data-date="${dateStr}" data-hour="${h}">`;
            slotEvents.forEach(ev => {
                // Высота зависит от длительности
                let height = 44;
                if (ev.timeStart && ev.timeEnd) {
                    const startMin = parseInt(ev.timeStart.split(':')[0]) * 60 + parseInt(ev.timeStart.split(':')[1]);
                    const endMin = parseInt(ev.timeEnd.split(':')[0]) * 60 + parseInt(ev.timeEnd.split(':')[1]);
                    height = Math.max(28, ((endMin - startMin) / 60) * 48 - 4);
                }
                html += `<div class="day-event event-cat-${ev.category}${ev.completed ? ' event-completed' : ''}" data-event-id="${ev.id}" style="height:${height}px;${ev.color ? 'background-color:'+ev.color+';color:#fff' : ''}">`;
                html += `<div class="event-time-label">${Utils.formatTimeRange(ev.timeStart, ev.timeEnd)}</div>`;
                html += (ev.completed ? '✓ ' : '') + Utils.escapeHtml(ev.title);
                html += '</div>';
            });
            html += '</div>';
        });
        html += '</div></div>';

        this.container.innerHTML = html;
        this._bindDayClicks();
    },

    _bindDayClicks() {
        this.container.querySelectorAll('.day-event, .day-allday-event').forEach(el => {
            el.addEventListener('click', (e) => {
                const checkEl = e.target.closest('.event-check-btn');
                if (checkEl) {
                    e.stopPropagation();
                    Events.toggleComplete(checkEl.dataset.eventId);
                    return;
                }
                e.stopPropagation();
                Events.openModal(el.dataset.eventId);
            });
        });

        this.container.querySelectorAll('.day-slot').forEach(cell => {
            cell.addEventListener('dblclick', () => {
                const date = cell.dataset.date;
                const hour = String(cell.dataset.hour).padStart(2, '0') + ':00';
                Events.openModal(null, date, hour);
            });
        });
    }
};
