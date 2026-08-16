/* ===== planner_sync.gs — Синхронизация Планировщика =====
 *
 * Развернуть в Google Таблице:
 * 1. Создать таблицу с листами: events, goals, notes, config
 * 2. Лист "config": ячейка A1 = токен (случайная строка)
 * 3. Листы events/goals/notes: строка 1 = заголовки колонок
 *
 * Заголовки:
 *   events: id | title | date | endDate | timeStart | timeEnd | category |
 *           priority | repeat | reminder | description | color | completed | completedAt |
 *           createdAt | updatedAt
 *   goals:  id | title | description | category | deadline | progress | status |
 *           createdAt | updatedAt
 *   notes:  id | title | content | date | category | createdAt | updatedAt
 *
 * Деплой: Публикация → Развернуть как веб-приложение → Любой, даже анонимный
 */

var SHEET_NAMES = {
  events: 'events',
  goals: 'goals',
  notes: 'notes',
  config: 'config'
};

function _getToken() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var configSheet = ss.getSheetByName(SHEET_NAMES.config);
  if (!configSheet) return '';
  var token = configSheet.getRange('A1').getValue();
  return token ? token.toString().trim() : '';
}

function _checkToken(token) {
  var expected = _getToken();
  if (!expected) return true; // если токен не задан — не проверять
  return token === expected;
}

function _sheetToArray(sheetName) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return [];
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return []; // только заголовки
  var headers = data[0];
  var result = [];
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0]) continue; // без id — пропускаем
    var obj = {};
    for (var j = 0; j < headers.length; j++) {
      var key = headers[j];
      if (key) obj[key] = row[j];
    }
    result.push(obj);
  }
  return result;
}

function _arrayToSheet(sheetName, items, headers) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }

  // Очищаем старые данные (кроме заголовков)
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).clearContent();
  }

  // Пишем новые данные
  if (items.length === 0) return;

  var rows = [];
  for (var i = 0; i < items.length; i++) {
    var row = [];
    for (var j = 0; j < headers.length; j++) {
      var val = items[i][headers[j]];
      row.push(val !== undefined && val !== null ? val : '');
    }
    rows.push(row);
  }
  sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
}

function _syncSheet(sheetName, incoming, headers) {
  // Читаем текущие данные
  var existing = _sheetToArray(sheetName);
  var existingMap = {};
  for (var i = 0; i < existing.length; i++) {
    existingMap[existing[i].id] = existing[i];
  }

  // Мержим: входящие записи перезаписывают существующие если новее
  for (var i = 0; i < incoming.length; i++) {
    var item = incoming[i];
    var existingItem = existingMap[item.id];
    if (!existingItem) {
      // Новая запись
      existingMap[item.id] = item;
    } else {
      // Сравниваем updatedAt — побеждает более свежий
      var incomingTime = new Date(item.updatedAt || 0).getTime();
      var existingTime = new Date(existingItem.updatedAt || 0).getTime();
      if (incomingTime > existingTime) {
        existingMap[item.id] = item;
      }
    }
  }

  // Удаляем записи из _deleted
  // (удаления обрабатываются через переданный массив _deleted)

  // Конвертируем обратно в массив
  var result = [];
  for (var id in existingMap) {
    result.push(existingMap[id]);
  }
  return result;
}

var EVENTS_HEADERS = ['id', 'title', 'date', 'endDate', 'timeStart', 'timeEnd',
  'category', 'priority', 'repeat', 'reminder', 'description', 'color',
  'completed', 'completedAt', 'createdAt', 'updatedAt'];

var GOALS_HEADERS = ['id', 'title', 'description', 'category', 'deadline',
  'progress', 'status', 'createdAt', 'updatedAt'];

var NOTES_HEADERS = ['id', 'title', 'content', 'date', 'category',
  'createdAt', 'updatedAt'];

/* ===== doGet — чтение данных ===== */
function doGet(e) {
  try {
    var action = e.parameter.action || 'getAll';
    var token = e.parameter.token || '';

    if (!_checkToken(token)) {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: 'invalid_token' })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    if (action === 'getAll') {
      var events = _sheetToArray(SHEET_NAMES.events);
      var goals = _sheetToArray(SHEET_NAMES.goals);
      var notes = _sheetToArray(SHEET_NAMES.notes);
      return ContentService.createTextOutput(
        JSON.stringify({ ok: true, events: events, goals: goals, notes: notes })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    if (action === 'ping') {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: true, pong: true })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: 'unknown_action' })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/* ===== doPost — синхронизация ===== */
function doPost(e) {
  try {
    var action = e.parameter.action || 'sync';
    var token = e.parameter.token || '';

    if (!_checkToken(token)) {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: 'invalid_token' })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    var body = JSON.parse(e.postData.contents);

    if (action === 'sync') {
      // Обрабатываем удаления
      var deleted = body._deleted || [];
      var sheetsToDeleteFrom = {
        events: deleted.filter(function(d) { return d.type === 'event'; }).map(function(d) { return d.id; }),
        goals: deleted.filter(function(d) { return d.type === 'goal'; }).map(function(d) { return d.id; }),
        notes: deleted.filter(function(d) { return d.type === 'note'; }).map(function(d) { return d.id; })
      };

      // Мержим и записываем events
      var mergedEvents = _syncSheet(SHEET_NAMES.events, body.events || [], EVENTS_HEADERS);
      // Удаляем помеченные
      if (sheetsToDeleteFrom.events.length > 0) {
        var delSet = {};
        sheetsToDeleteFrom.events.forEach(function(id) { delSet[id] = true; });
        mergedEvents = mergedEvents.filter(function(ev) { return !delSet[ev.id]; });
      }
      _arrayToSheet(SHEET_NAMES.events, mergedEvents, EVENTS_HEADERS);

      // Мержим и записываем goals
      var mergedGoals = _syncSheet(SHEET_NAMES.goals, body.goals || [], GOALS_HEADERS);
      if (sheetsToDeleteFrom.goals.length > 0) {
        var delSet2 = {};
        sheetsToDeleteFrom.goals.forEach(function(id) { delSet2[id] = true; });
        mergedGoals = mergedGoals.filter(function(g) { return !delSet2[g.id]; });
      }
      _arrayToSheet(SHEET_NAMES.goals, mergedGoals, GOALS_HEADERS);

      // Мержим и записываем notes
      var mergedNotes = _syncSheet(SHEET_NAMES.notes, body.notes || [], NOTES_HEADERS);
      if (sheetsToDeleteFrom.notes.length > 0) {
        var delSet3 = {};
        sheetsToDeleteFrom.notes.forEach(function(id) { delSet3[id] = true; });
        mergedNotes = mergedNotes.filter(function(n) { return !delSet3[n.id]; });
      }
      _arrayToSheet(SHEET_NAMES.notes, mergedNotes, NOTES_HEADERS);

      return ContentService.createTextOutput(
        JSON.stringify({
          ok: true,
          events: mergedEvents,
          goals: mergedGoals,
          notes: mergedNotes
        })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: 'unknown_action' })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
