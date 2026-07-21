import sys
import os
import unittest
from unittest.mock import MagicMock

# Ajusta o path para importar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hardware import MockBackend
from fechadura import FechaduraApp, State

class TestFechadura(unittest.TestCase):
    def setUp(self):
        self.hw = MockBackend()
        self.hw.mock_distance = 5.0 # Simula porta fechada
        self.app = FechaduraApp(self.hw, password="123")
        self.app.transition_to_idle()

    def test_initial_state(self):
        self.assertEqual(self.app.state, State.IDLE)
        # Verifica se o LCD foi inicializado com as mensagens de idle
        self.assertTrue(any("LOCKED" in str(e[2]) for e in self.hw.events))

    def test_correct_password(self):
        # Simula digitação da senha
        self.hw.mock_key = "1"
        self.app.loop_iteration()
        self.assertEqual(self.app.state, State.INPUT)

        self.hw.mock_key = "2"
        self.app.loop_iteration()

        self.hw.mock_key = "3"
        self.app.loop_iteration()

        # Confirma
        self.hw.mock_key = "#"
        self.app.loop_iteration()
        
        self.assertEqual(self.app.state, State.UNLOCKED)
        self.assertTrue(any("DESTRANCADA" in str(e[2]) for e in self.hw.events))
        
        # Verifica beep do buzzer na abertura
        self.assertTrue(any(e[1] == "buzzer" and e[2] == "on" for e in self.hw.events))

    def test_incorrect_password(self):
        # Simula digitação da senha errada
        self.hw.mock_key = "9"
        self.app.loop_iteration()
        
        # Confirma
        self.hw.mock_key = "#"
        self.app.loop_iteration()
        
        # Deve retornar para IDLE pois failed_attempts < max
        self.assertEqual(self.app.state, State.IDLE)
        self.assertEqual(self.app.failed_attempts, 1)

    def test_cooldown(self):
        # Erra a senha 3 vezes
        for _ in range(3):
            self.hw.mock_key = "9"
            self.app.loop_iteration()
            self.hw.mock_key = "#"
            self.app.loop_iteration()

        self.assertEqual(self.app.state, State.COOLDOWN)
        self.assertEqual(self.app.failed_attempts, 3)

    def test_door_sensor_tamper(self):
        # Força o sensor a dizer que a porta está aberta enquanto o estado é IDLE
        self.hw.mock_distance = 50.0 # > 10cm significa aberta
        
        # Na próxima iteração, o alarme deve disparar
        self.app.loop_iteration()
        
        # Verifica mensagem de alarme
        self.assertTrue(any("VIOLADA" in str(e[2]) for e in self.hw.events))

if __name__ == '__main__':
    unittest.main()
