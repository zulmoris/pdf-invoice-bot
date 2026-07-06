Set WshShell = CreateObject("WScript.Shell")
' Указываем точный путь к твоему Python и к скрипту bot.py
' ВНИМАНИЕ: пути должны быть в кавычках, так как в них есть пробелы
WshShell.Run """C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe"" ""C:\Users\user\Desktop\BotPython\bot.py""", 0, False