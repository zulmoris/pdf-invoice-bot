// ==========================================
// НАСТРОЙКИ — ПОМЕНЯЙ НА СВОИ
// ==========================================
var BOT_TOKEN = "7690342745:AAEh5i7YihlNwYzmvDPb_rBWom_IZsYnemE";
var TEST_CHAT_ID = "438544636"; // Тестовый ID (пока шлём сюда)

// Столбцы (номера, не буквы!)
var COL_INVOICE    = 1;  // A — № счёта
var COL_CLIENT     = 3;  // C — Клиент
var COL_DESIGNER   = 4;  // D — Дизайнер
var COL_NOTIFIED   = 6;  // F — Уведомлено
var COL_POSITIONS  = 7;  // G — Позиции ПОСТ
var COL_SUPPLIER   = 8;  // H — Поставщик
var COL_TK_ARRIVAL = 13; // M — Дата прихода ТК КЗН
var COL_WAREHOUSE  = 14; // N — Дата прихода СКЛАД
var COL_MANAGER    = 16; // P — Менеджер

// ==========================================
// onEdit — срабатывает при редактировании таблицы
// ==========================================
function onEdit(e) {
  try {
    var sheet = e.source.getActiveSheet();
    if (sheet.getName() === "Telegram ID") return;

    var range = e.range;
    var col = range.getColumn();
    var row = range.getRow();

    // Срабатываем ТОЛЬКО при редактировании M (13) или N (14)
    if (col !== COL_TK_ARRIVAL && col !== COL_WAREHOUSE) return;
    if (row <= 1) return;

    var notified = sheet.getRange(row, COL_NOTIFIED).getValue();
    if (notified === "УВЕДОМЛЕНО") return;

    // ИЩЕМ № СЧЁТА — идём вверх если ячейка пустая (объединённые ячейки)
    var invoice = sheet.getRange(row, COL_INVOICE).getValue();
    if (!invoice) {
      for (var r = row - 1; r >= 2; r--) {
        var val = sheet.getRange(r, COL_INVOICE).getValue();
        if (val) {
          invoice = val;
          break;
        }
      }
    }

    if (!invoice) return;

    SpreadsheetApp.flush();
    checkAndNotify(sheet, invoice);

  } catch (error) {
    Logger.log("ОШИБКА onEdit: " + error);
  }
}

// ==========================================
// ПРОВЕРКА И ОТПРАВКА УВЕДОМЛЕНИЙ
// ==========================================
function checkAndNotify(sheet, invoice) {
  var data = sheet.getDataRange().getValues();

  // Находим все строки счёта (учитывая объединённые ячейки)
  var invoiceRows = [];
  var firstMatchRow = -1;

  for (var i = 1; i < data.length; i++) {
    var val = data[i][COL_INVOICE - 1];
    if (String(val) == String(invoice)) {
      if (firstMatchRow === -1) firstMatchRow = i;
      invoiceRows.push(i);
    } else if (val === "" && firstMatchRow !== -1) {
      invoiceRows.push(i);
    } else if (val !== "" && firstMatchRow !== -1) {
      break;
    }
  }

  if (invoiceRows.length === 0) return;

  // Проверяем: у КАЖДОЙ строки заполнено ХОТЯ БЫ ОДНО из двух (ТК КЗН или СКЛАД)
  var allComplete = true;
  for (var j = 0; j < invoiceRows.length; j++) {
    var r = invoiceRows[j];
    var tkArrival = data[r][COL_TK_ARRIVAL - 1];
    var warehouse = data[r][COL_WAREHOUSE - 1];
    if (!tkArrival && !warehouse) {
      allComplete = false;
      break;
    }
  }

  if (!allComplete) return;

  // Собираем данные из первой строки
  var client   = data[invoiceRows[0]][COL_CLIENT - 1] || "—";
  var designer = data[invoiceRows[0]][COL_DESIGNER - 1] || "—";
  var manager  = data[invoiceRows[0]][COL_MANAGER - 1] || "—";

  // ==========================================
  // Формируем ДВА сообщения
  // ==========================================

  // ПОЛНОЕ сообщение (с поставщиками) — для менеджера, руководителя, общего чата
  var compositionFull = "";
  for (var k = 0; k < invoiceRows.length; k++) {
    var r2 = invoiceRows[k];
    var supplierF  = data[r2][COL_SUPPLIER - 1] || "?";
    var positionsF = data[r2][COL_POSITIONS - 1] || "?";
    var locationF  = getLocation(data, r2);
    compositionFull += "  • поз. " + positionsF + " (" + supplierF + ") — " + locationF + "\n";
  }

  var messageFull = "📦 Счёт №" + invoice + " — все позиции пришли\n" +
                    "👤 Клиент: " + client + "\n" +
                    "👤 Дизайнер: " + designer + "\n" +
                    "👷 Менеджер: " + manager + "\n" +
                    "📋 Состав:\n" + compositionFull;

  // СОКРАЩЁННОЕ сообщение (без поставщиков) — для клиента и дизайнера
  var compositionBrief = "";
  for (var m = 0; m < invoiceRows.length; m++) {
    var r3 = invoiceRows[m];
    var positionsB = data[r3][COL_POSITIONS - 1] || "?";
    var locationB  = getLocation(data, r3);
    compositionBrief += "  • поз. " + positionsB + " — " + locationB + "\n";
  }

  var messageBrief = "📦 Счёт №" + invoice + " — все позиции пришли\n" +
                      "👤 Клиент: " + client + "\n" +
                      "📋 Состав:\n" + compositionBrief;

  // ==========================================
  // Определяем получателей и отправляем
  // ==========================================
  var groups = getRecipientGroups(manager, designer, invoice);

  // ==========================================
  // ОТПРАВКА УВЕДОМЛЕНИЙ
  // ==========================================
  // ⚠️ ВРЕМЕННО: отправляем ТОЛЬКО в рабочий чат (TEST_CHAT_ID)
  // Менеджеры, дизайнеры, клиенты — отключены для устранения спама.
  // Логика сохранена, можно вернуть убрав комментарии (//) ниже.

  // Отправляем полное сообщение в рабочий чат
  sendTelegram(TEST_CHAT_ID, messageFull);

  /*  === ОТКЛЮЧЕНО ДО УСТРАНЕНИЯ СПАМА ===
  var groups = getRecipientGroups(manager, designer, invoice);

  // Группа 1: ПОЛНОЕ сообщение, БЕЗ кнопок
  for (var g1 = 0; g1 < groups.full.length; g1++) {
    sendTelegram(groups.full[g1], messageFull);
  }

  // Группа 2: СОКРАЩЁННОЕ сообщение, С кнопками
  var keyboard = buildInlineKeyboard(invoice);
  for (var g2 = 0; g2 < groups.brief.length; g2++) {
    sendTelegram(groups.brief[g2], messageBrief, keyboard);
  }
  === КОНЕЦ ОТКЛЮЧЁННОГО БЛОКА ===  */

  // Ставим "УВЕДОМЛЕНО" во все строки
  for (var n = 0; n < invoiceRows.length; n++) {
    sheet.getRange(invoiceRows[n] + 1, COL_NOTIFIED).setValue("УВЕДОМЛЕНО");
  }

  Logger.log("Уведомление отправлено в рабочий чат для счёта " + invoice);
}

// ==========================================
// ОПРЕДЕЛЯЕМ МЕСТО ПРИХОДА
// ==========================================
function getLocation(data, row) {
  var tkArrival = data[row][COL_TK_ARRIVAL - 1];
  var warehouse = data[row][COL_WAREHOUSE - 1];

  if (tkArrival && warehouse) return "Склад + ТК КЗН";
  if (warehouse) return "Склад";
  if (tkArrival) return "ТК КЗН";
  return "—";
}

// ==========================================
// ГРУППЫ ПОЛУЧАТЕЛЕЙ
// ==========================================
function getRecipientGroups(managerName, designerName, invoice) {
  var full = [];   // менеджер, руководитель, общий чат
  var brief = [];  // дизайнер, клиент

  // 1. Общий чат — всегда в full
  full.push(TEST_CHAT_ID);

  // Читаем справочник
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tgSheet = ss.getSheetByName("Telegram ID");
  if (!tgSheet) {
    return {full: full, brief: brief};
  }
  var tgData = tgSheet.getDataRange().getValues();

  // 2. Менеджеры (делим по "/")
  var managerNames = String(managerName).split("/");
  for (var i = 0; i < managerNames.length; i++) {
    var mName = managerNames[i].trim().toLowerCase();
    if (!mName) continue;
    for (var j = 1; j < tgData.length; j++) {
      var tgName = String(tgData[j][0]).trim().toLowerCase();
      var tgId = String(tgData[j][1]).trim();
      var tgType = String(tgData[j][2]).trim().toLowerCase();
      if (tgName === mName && tgId && tgType === "менеджер") {
        full.push(tgId);
      }
    }
  }

  // 3. Руководители — всегда в full
  for (var k = 1; k < tgData.length; k++) {
    var rType = String(tgData[k][2]).trim().toLowerCase();
    var rId = String(tgData[k][1]).trim();
    if (rType === "руководитель" && rId) {
      full.push(rId);
    }
  }

  // 4. Дизайнеры — в brief (с кнопками)
  var designerNames = String(designerName).split("/");
  for (var d = 0; d < designerNames.length; d++) {
    var dName = designerNames[d].trim().toLowerCase();
    if (!dName) continue;
    for (var e = 1; e < tgData.length; e++) {
      var dgName = String(tgData[e][0]).trim().toLowerCase();
      var dgId = String(tgData[e][1]).trim();
      var dgType = String(tgData[e][2]).trim().toLowerCase();
      if (dgName === dName && dgId && dgType === "дизайнер") {
        brief.push(dgId);
      }
    }
  }

  // 5. Клиент — ищем по номеру счёта (тип "клиент")
  for (var c = 1; c < tgData.length; c++) {
    var cName = String(tgData[c][0]).trim();
    var cId = String(tgData[c][1]).trim();
    var cType = String(tgData[c][2]).trim().toLowerCase();
    if (cName == String(invoice) && cId && cType === "клиент") {
      brief.push(cId);
    }
  }

  // Убираем дубликаты в каждой группе
  full = uniqueArray(full);
  brief = uniqueArray(brief);

  return {full: full, brief: brief};
}

function uniqueArray(arr) {
  var result = [];
  for (var i = 0; i < arr.length; i++) {
    if (result.indexOf(arr[i]) === -1) result.push(arr[i]);
  }
  return result;
}

// ==========================================
// INLINE-КЛАВИАТУРА (КНОПКИ)
// ==========================================
function buildInlineKeyboard(invoice) {
  return {
    inline_keyboard: [
      [
        {text: "🚚 Заказать доставку", callback_data: "delivery:" + invoice},
        {text: "🏠 Заберу сам", callback_data: "pickup:" + invoice}
      ],
      [
        {text: "📞 Свяжитесь со мной", callback_data: "contact:" + invoice}
      ]
    ]
  };
}

// ==========================================
// ОТПРАВКА В TELEGRAM (с поддержкой кнопок)
// ==========================================
function sendTelegram(chatId, text, keyboard) {
  var url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage";

  var payload = {
    chat_id: chatId,
    text: text
  };

  if (keyboard) {
    payload.reply_markup = keyboard;
  }

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var result = JSON.parse(response.getContentText());
    if (!result.ok) {
      Logger.log("Telegram API ошибка: " + response.getContentText());
    }
    return result;
  } catch (error) {
    Logger.log("Ошибка отправки Telegram: " + error);
    return null;
  }
}

// ==========================================
// doPost — ОБРАБОТКА СООБЩЕНИЙ И КНОПОК
// ==========================================
function doPost(e) {
  // ==========================================
  // БЛОКИРОВКА: только один запрос за раз
  // ==========================================
  // Apps Script может обрабатывать запросы параллельно.
  // LockService заставляет их выстроиться в очередь.
  var lock = LockService.getScriptLock();
  lock.tryLock(30000); // ждём до 30 секунд

  try {
    var data = JSON.parse(e.postData.contents);

    // ==========================================
    // ДЕДУПЛИКАЦИЯ по уникальному ID
    // ==========================================
    // Telegram присылает каждому событию уникальный ID.
    // При повторе (ретрае) — ID тот же самый.
    // Используем это, чтобы не обрабатывать дубль.
    var cache = CacheService.getScriptCache();
    var updateId = "";

    if (data.callback_query) {
      updateId = "cb_" + data.callback_query.id;
    } else if (data.message) {
      updateId = "msg_" + data.message.message_id;
    }

    // Если этот запрос уже обрабатывался — просто выходим
    if (updateId && cache.get(updateId)) {
      Logger.log("Дубль запроса, пропускаем: " + updateId);
      if (lock.hasLock()) lock.releaseLock();
      return ContentService.createTextOutput("ok");
    }

    // Отмечаем запрос как обработанный (на 10 минут)
    if (updateId) {
      cache.put(updateId, "done", 600);
    }

    // Обрабатываем
    if (data.callback_query) {
      handleCallback(data.callback_query);
    } else if (data.message) {
      handleMessage(data.message);
    }

  } catch (error) {
    Logger.log("doPost ошибка: " + error);
  } finally {
    if (lock.hasLock()) lock.releaseLock();
  }

  return ContentService.createTextOutput("ok");
}

// ==========================================
// ОБРАБОТКА НАЖАТИЙ КНОПОК
// ==========================================
function handleCallback(callback) {
  var chatId = String(callback.message.chat.id);
  var userId = String(callback.from.id);
  var userName = callback.from.first_name || "Без имени";
  var data = callback.data; // например "delivery:767"

  var parts = data.split(":");
  var action = parts[0];   // delivery, pickup, contact
  var invoice = parts[1];  // номер счёта

  // Подтверждаем нажатие (убираем "часики" на кнопке)
  answerCallback(callback.id);

  if (action === "delivery") {
    // ЗАКАЗАТЬ ДОСТАВКУ
    // Сохраняем в кэш: ждём ответ от этого пользователя (10 минут)
    var cache = CacheService.getScriptCache();
    cache.put("delivery_pending_" + chatId, invoice + "|" + userName, 600);

    var questions = "🚚 Для оформления доставки ответьте на это сообщение, указав:\n\n" +
                    "1. Адрес доставки\n" +
                    "2. Контакт для связи\n" +
                    "3. Нужна ли разгрузка (если да — этаж, лифт, проезд, ЖК)\n" +
                    "4. Для юр.лиц: ЭДО или доверенность/печать на месте?\n" +
                    "   (если оплата от физ.лица — напишите «нет»)\n\n" +
                    "✍️ Напишите ответ ОДНИМ сообщением:";
    sendTelegram(chatId, questions);

  } else if (action === "pickup") {
    // ЗАБЕРУ САМ
    sendTelegram(chatId, "👍 Менеджер свяжется с вами и объяснит, как и где забрать товар.");

    var notifyMsg = "🏠 КЛИЕНТ ЗАБЕРЁТ САМ\n" +
                    "📦 Счёт №" + invoice + "\n" +
                    "👤 От: " + userName;
    notifyManagers(notifyMsg);

  } else if (action === "contact") {
    // СВЯЖИТЕСЬ СО МНОЙ
    sendTelegram(chatId, "📞 Менеджер свяжется с вами в ближайшее время.");

    var notifyMsg2 = "📞 ПРОСЬБА СВЯЗАТЬСЯ\n" +
                     "📦 Счёт №" + invoice + "\n" +
                     "👤 От: " + userName;
    notifyManagers(notifyMsg2);
  }
}

// ==========================================
// ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
// ==========================================
function handleMessage(message) {
  var chatId = String(message.chat.id);
  var text = message.text || "";
  var userName = message.from.first_name || "Без имени";

  // Команда /start — выдаём ID
  if (text === "/start") {
    var reply = "🔑 Ваш Telegram ID: " + chatId + "\n\n" +
                "Отправьте это число менеджеру для привязки.";
    sendTelegram(chatId, reply);
    return;
  }

  // Проверяем: ждём ли мы ответ про доставку?
  var cache = CacheService.getScriptCache();
  var pending = cache.get("delivery_pending_" + chatId);

  if (pending) {
    // Это ответ на доставку!

    // СПАМ-ЗАЩИТА: сразу удаляем флаг "ждём доставки",
    // чтобы повторные запросы Telegram не отправили заявку дважды
    cache.remove("delivery_pending_" + chatId);

    var parts = pending.split("|");
    var invoice = parts[0];
    var cachedName = parts[1] || userName;

    // Дополнительная блокировка на 60 сек (от дублей запроса)
    var msgLock = "msg_processed_" + chatId + "_" + invoice;
    if (cache.get(msgLock)) {
      Logger.log("Спам-защита: ответ доставки уже обработан для " + chatId);
      return;
    }
    cache.put(msgLock, "locked", 60);

    // Уведомляем менеджеров + общий чат
    var deliveryMsg = "🚚 ЗАЯВКА НА ДОСТАВКУ\n" +
                      "📦 Счёт №" + invoice + "\n" +
                      "👤 От: " + cachedName + "\n\n" +
                      "📝 Данные для доставки:\n" + text;
    notifyManagers(deliveryMsg);

    // Подтверждаем клиенту
    sendTelegram(chatId, "✅ Ваша заявка на доставку передана менеджеру.\nМы свяжемся с вами.");

    // Кэш уже очищен выше (для защиты от дублей)
    return;
  }

  // Обычное сообщение (не команда, не доставка) — игнорируем
  Logger.log("Сообщение от " + chatId + ": " + text);
}

// ==========================================
// УВЕДОМЛЕНИЕ МЕНЕДЖЕРОВ + ОБЩЕГО ЧАТА
// ==========================================
function notifyManagers(text) {
  // Пока шлём в общий чат (TEST_CHAT_ID)
  sendTelegram(TEST_CHAT_ID, text);

  // TODO: добавить поиск менеджеров по счёту и отправку им в личку
}

// ==========================================
// ПОДТВЕРЖДЕНИЕ НАЖАТИЯ КНОПКИ
// ==========================================
function answerCallback(callbackId) {
  var url = "https://api.telegram.org/bot" + BOT_TOKEN + "/answerCallbackQuery";
  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({callback_query_id: callbackId}),
    muteHttpExceptions: true
  };
  try {
    UrlFetchApp.fetch(url, options);
  } catch (e) {
    Logger.log("answerCallback ошибка: " + e);
  }
}
