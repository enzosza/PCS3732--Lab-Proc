# Fechadura eletrônica — Raspberry Pi 3 + Freenove Projects Board v1.2

Implementação em Python da lógica completa de uma fechadura eletrônica com:

- entrada de senha em teclado matricial 4x4;
- LCD1602 por I2C para feedback visual;
- servomotor como atuador da tranca;
- buzzer ativo para feedback e alarme;
- sensor ultrassônico para identificar porta aberta/fechada;
- bloqueio temporário após três senhas incorretas;
- detecção de abertura forçada;
- armazenamento da senha com PBKDF2-HMAC-SHA256 e salt;
- registros textuais e eventos estruturados em JSON Lines;
- máquina de estados e sinais sonoros não bloqueantes.

## Arquivo principal

`src/electronic_lock.py`

## Mapeamento BCM

| Componente | GPIO |
|---|---|
| Teclado — linhas | 16, 20, 21, 26 |
| Teclado — colunas | 19, 13, 6, 5 |
| Servo | 18 |
| Buzzer ativo | 12 |
| Ultrassônico — trigger | 14 |
| Ultrassônico — echo | 15 |
| LCD I2C — SDA/SCL | 2/3 |

## Teclas

- `0` a `9`: inserir senha;
- `*`: apagar último dígito;
- `D`: limpar entrada;
- `#`: confirmar;
- `A`: solicitar fechamento manual;
- `B`: mostrar distância do sensor.

Na ausência de `config/credentials.json`, a primeira execução cria a senha de laboratório `1234`. Altere-a antes da demonstração usando `scripts/set_password.py`.

## Estrutura

- `src/`: aplicação e drivers;
- `scripts/`: testes isolados de cada componente;
- `tests/`: testes automatizados sem acesso às GPIOs;
- `config/lock_config.json`: parâmetros ajustáveis;
- `PINOUT.txt`: pinagem e conflitos relevantes da placa.

## Arquivos gerados durante a execução

- `config/credentials.json`;
- `logs/electronic_lock.log`;
- `logs/events.jsonl`.
