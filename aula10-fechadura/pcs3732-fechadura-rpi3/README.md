# Inicialização da Fechadura Eletrônica (Raspberry Pi)

## Passo 1: Habilitar o Barramento I2C
O display LCD utiliza comunicação I2C. Por padrão, o Raspbian/Raspberry Pi OS vem com o I2C desativado.

1. Abra o terminal do Raspberry Pi e digite:
   ```bash
   sudo raspi-config
   ```
2. Navegue até **Interface Options** (ou *Interfacing Options* em versões mais antigas).
3. Selecione **I2C**.
4. Responda **"Yes"** para habilitar o módulo do kernel I2C.
5. Saia do `raspi-config` (selecione *Finish*). Se pedir para reiniciar, aceite.

## Passo 2: Verificar a Conexão do FNK0054
Se estiver utilizando a placa base/breadboard do kit Freenove FNK0054:
1. Certifique-se de que os cabos do **LCD 1602 (módulo I2C)** estão ligados (GND, VCC=5V, SDA, SCL).
2. Verifique se o módulo foi reconhecido no barramento rodando no terminal:
   ```bash
   sudo i2cdetect -y 1
   ```
   > Observação: Você deve ver um endereço (normalmente `0x27` ou `0x3f`) aparecer na grade. O código atual usa `0x27` por padrão.

## Passo 3: Instalar as Dependências
O sistema requer as bibliotecas `RPi.GPIO` e `smbus`. Elas geralmente já vêm instaladas no Raspberry Pi OS, mas você pode garantir rodando:

```bash
cd aula10-fechadura/pcs3732-fechadura-rpi3
sudo apt-get update
sudo apt-get install python3-rpi.gpio python3-smbus
```
*(Alternativamente, você pode usar `pip3 install -r requirements.txt` caso utilize um ambiente virtual Python isolado)*.

## Passo 4: Executar a Fechadura
Devido ao uso direto dos pinos de hardware com `RPi.GPIO`, é recomendado (ou até obrigatório dependendo da sua versão do SO) rodar o script principal com permissões de administrador:

```bash
sudo python3 src/fechadura.py
```

## Passo 5: Uso do Sistema
- O LCD deverá exibir **STATUS: LOCKED** e **DIGITE A SENHA**.
- Digite a senha no teclado matricial (A senha padrão programada é `1234`) e pressione a tecla **`#`** para confirmar.
- Para apagar a senha digitada, aperte **`*`**.
- Múltiplas tentativas erradas ativarão o sistema de *cooldown* que ignorará entradas temporariamente.
- Se a porta abrir sem a senha (o sensor ultrassônico acusar a abertura com o sistema em `IDLE`), o buzzer soará o alarme!
