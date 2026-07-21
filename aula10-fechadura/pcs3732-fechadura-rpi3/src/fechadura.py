import argparse
import signal
import sys
import time
from enum import Enum
from typing import Optional

from hardware import HardwareBackend, MockBackend, RPiHardwareBackend

class State(Enum):
    IDLE = 1
    INPUT = 2
    PROCESSING = 3
    COOLDOWN = 4
    UNLOCKED = 5

class FechaduraApp:
    def __init__(self, hardware: HardwareBackend, password: str = "1234"):
        self.hw = hardware
        self.password = password
        self.state = State.IDLE
        
        self.input_buffer = ""
        self.failed_attempts = 0
        self.max_attempts = 3
        
        self.cooldown_end_time = 0.0
        self.unlocked_end_time = 0.0
        
        self.running = False
        
        # Sensor threshold
        self.DOOR_CLOSED_CM = 10.0

    def is_door_closed(self) -> bool:
        dist = self.hw.get_distance_cm()
        # Se dist for negativa, houve erro de leitura, assume fechada por segurança
        return dist < self.DOOR_CLOSED_CM or dist < 0

    def run(self):
        self.running = True
        self.hw.lcd_clear()
        self.hw.lcd_print(" INICIANDO... ", 1)
        time.sleep(1)
        
        self.transition_to_idle()

        while self.running:
            self.loop_iteration()
            time.sleep(0.05) # Loop não bloqueante principal

    def stop(self):
        self.running = False
        self.hw.close()

    def transition_to_idle(self):
        self.state = State.IDLE
        self.input_buffer = ""
        self.hw.lcd_clear()
        self.hw.lcd_print(" STATUS: LOCKED ", 1)
        if not self.is_door_closed():
            self.hw.lcd_print(" PORTA ABERTA! ", 2)
        else:
            self.hw.lcd_print(" DIGITE A SENHA ", 2)

    def transition_to_input(self, first_char: str):
        self.state = State.INPUT
        self.input_buffer = first_char
        self.update_lcd_input()

    def update_lcd_input(self):
        self.hw.lcd_clear()
        self.hw.lcd_print(" SENHA: ", 1)
        # Mostrar asteriscos para ofuscação
        self.hw.lcd_print("*" * len(self.input_buffer), 2)

    def transition_to_processing(self):
        self.state = State.PROCESSING
        self.hw.lcd_clear()
        self.hw.lcd_print(" VERIFICANDO... ", 1)
        
        if self.input_buffer == self.password:
            self.success()
        else:
            self.fail()

    def success(self):
        self.failed_attempts = 0
        self.state = State.UNLOCKED
        self.hw.lcd_clear()
        self.hw.lcd_print(" ACESSO LIBERADO", 1)
        self.hw.lcd_print(" PORTA DESTRANCADA", 2)
        
        # Bip curto
        self.hw.buzzer_on()
        time.sleep(0.2)
        self.hw.buzzer_off()
        
        self.unlocked_end_time = time.time() + 5.0 # Fica destrancada por 5 segundos

    def fail(self):
        self.failed_attempts += 1
        self.hw.lcd_clear()
        self.hw.lcd_print(" ACESSO NEGADO! ", 1)
        
        # Bip longo
        self.hw.buzzer_on()
        time.sleep(1.0)
        self.hw.buzzer_off()
        
        if self.failed_attempts >= self.max_attempts:
            self.state = State.COOLDOWN
            self.cooldown_end_time = time.time() + 10.0 # Bloqueio de 10 segundos
            self.hw.lcd_print(" SISTEMA BLOQUEADO", 2)
        else:
            time.sleep(1.0) # Espera mostrar a msg de erro
            self.transition_to_idle()

    def loop_iteration(self):
        # Verifica integridade (tampering básico) se a porta está aberta no modo IDLE
        if self.state == State.IDLE:
            if not self.is_door_closed():
                # A porta não deveria estar aberta se está trancada!
                self.hw.lcd_print(" ALARME! PORTA", 1)
                self.hw.lcd_print(" VIOLADA!", 2)
                self.hw.buzzer_on()
                time.sleep(0.5)
                self.hw.buzzer_off()
                return # Pula o resto até fechar
            else:
                self.hw.lcd_print(" DIGITE A SENHA ", 2)

        key = self.hw.scan_keypad()
        
        if self.state == State.IDLE:
            if key:
                self.transition_to_input(key)
                
        elif self.state == State.INPUT:
            if key:
                if key == '#': # Botão de confirmar
                    self.transition_to_processing()
                elif key == '*': # Botão de apagar/cancelar
                    self.transition_to_idle()
                elif len(self.input_buffer) < 8: # Limite de tamanho
                    self.input_buffer += key
                    self.update_lcd_input()
                    
        elif self.state == State.COOLDOWN:
            remaining = int(self.cooldown_end_time - time.time())
            if remaining <= 0:
                self.failed_attempts = 0
                self.transition_to_idle()
            else:
                self.hw.lcd_clear()
                self.hw.lcd_print(" SISTEMA BLOQUEADO", 1)
                self.hw.lcd_print(f" AGUARDE {remaining}s", 2)
                
        elif self.state == State.UNLOCKED:
            if time.time() > self.unlocked_end_time:
                # Re-tranca automaticamente
                self.transition_to_idle()

def main():
    parser = argparse.ArgumentParser(description="Fechadura Eletrônica")
    parser.add_argument("--dry-run", action="store_true", help="Executa com backend simulado (Mock)")
    args = parser.parse_args()

    if args.dry_run:
        hw = MockBackend()
    else:
        try:
            hw = RPiHardwareBackend()
        except Exception as e:
            print(f"Erro ao inicializar o hardware: {e}")
            sys.exit(1)

    app = FechaduraApp(hw)

    def signal_handler(sig, frame):
        print("\nEncerrando aplicação...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("Fechadura eletrônica iniciada. Pressione Ctrl+C para sair.")
    app.run()

if __name__ == "__main__":
    main()
