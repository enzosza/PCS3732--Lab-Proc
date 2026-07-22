ARQUIVO PRINCIPAL
  src/electronic_lock.py

CÓDIGOS AUXILIARES DE TESTE ISOLADO
  scripts/test_keypad.py
  scripts/test_lcd.py
  scripts/test_servo.py
  scripts/test_buzzer.py
  scripts/test_ultrasonic.py
  scripts/set_password.py

COMPORTAMENTO DO TECLADO
  Dígitos 0-9: compõem a senha
  *: apaga o último dígito
  D: limpa toda a entrada
  #: confirma a senha
  A: solicita fechamento manual, se a porta estiver fisicamente fechada
  B: mostra temporariamente a distância medida pelo sensor

CREDENCIAL INICIAL
  Se config/credentials.json não existir, a primeira execução cria a senha 1234.
  O arquivo armazena PBKDF2-HMAC-SHA256 com salt, nunca a senha em texto claro.

ARQUIVOS GERADOS
  config/credentials.json
  logs/electronic_lock.log
  logs/events.jsonl
