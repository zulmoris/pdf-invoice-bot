# -*- coding: utf-8 -*-
"""
Настройки развёртывания PDF-бота Аганим (какой Google-таблицей работает объект).

settings.json лежит в %APPDATA%/PDF-bot-Aganim/. Путь resolves через pathlib
(разворачивает symlink/..) и проверяется принадлежностью APPDATA.
Используется ботом и дашбордом.
"""
import os
import json
from pathlib import Path

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QkXocbAJu1a5rcu3XNEfpHnoF_mA5flgehjO6E7VIWM/edit?usp=sharing"

_APPDATA = Path(os.environ.get("APPDATA") or Path.home()).resolve()
_DIR = (_APPDATA / "PDF-bot-Aganim").resolve()
if _DIR.parent != _APPDATA:
    _DIR = _APPDATA  # проверка границ: не выходим за APPDATA
_FILE = _DIR / "settings.json"


def load_sheet_url() -> str:
    """URL таблицы из settings.json или '' если не задан."""
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            url = str(data.get("sheet_url", ""))
            if "docs.google.com" in url:
                return url
    except Exception:
        pass
    return ""


def save_sheet_url(url: str) -> bool:
    """Сохраняет URL таблицы. True при успехе."""
    if not url or "docs.google.com" not in url:
        return False
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        _FILE.write_text(
            json.dumps({"sheet_url": url}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return True
    except Exception:
        return False


def is_configured() -> bool:
    """Есть ли уже settings.json (не первый запуск)."""
    return _FILE.is_file()


# ---------- Валидация URL Apps Script (защита от SSRF) ----------
# Разрешён только https и только хост script.google.com.
from urllib.parse import urlparse

_ALLOWED_HOSTS = {"script.google.com"}


def is_valid_apps_script_url(url: str) -> bool:
    """True если URL — https://script.google.com/... (whitelist хоста)."""
    try:
        p = urlparse(str(url or ""))
        return p.scheme == "https" and p.netloc in _ALLOWED_HOSTS
    except Exception:
        return False


# ---------- config.json (папка счетов) ----------
_CONFIG = _DIR / "config.json"


def load_config() -> dict:
    """Читает config.json (folder_path). dict при ошибке."""
    try:
        data = json.loads(_CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(cfg: dict) -> bool:
    """Сохраняет config.json. True при успехе."""
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=4), encoding="utf-8")
        return True
    except Exception:
        return False


# ---------- Безопасный вызов Apps Script (анти-SSRF) ----------
import socket
import ipaddress
import urllib.request
import urllib.parse


def _host_ips_are_public(host: str) -> bool:
    """Резолвим хост и требуем, чтобы ВСЕ IP были публичными
    (блокируем приватные/loopback/link-local — защита от DNS-rebinding)."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except Exception:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return bool(infos)


def call_apps_script(base_url: str, params: dict, timeout: int = 30):
    """GET-запрос к https://script.google.com/... (строгий whitelist хоста,
    проверка резолва IP, редиректы не следуются без повторной проверки —
    urllib по умолчанию следует, поэтому хост перепроверяется на каждый шаг
    через собственный opener без автоматических redirect).
    Возвращает текст ответа или '' при ошибке/отказе валидации."""
    p = urlparse(str(base_url or ""))
    if p.scheme != "https" or p.netloc != "script.google.com":
        return ""
    if not _host_ips_are_public(p.netloc):
        return ""
    try:
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"https://script.google.com{p.path}?{qs}")
        # Безопасный opener: без автоматического следования редиректам
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
