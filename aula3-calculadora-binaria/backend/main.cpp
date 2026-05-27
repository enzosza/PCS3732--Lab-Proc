#include <Arduino.h>

const int PINOS_LEDS[] = {12, 13, 14, 15};

void setup() {
    pinMode(PINOS_LEDS[0], OUTPUT);
    pinMode(PINOS_LEDS[1], OUTPUT);
    pinMode(PINOS_LEDS[2], OUTPUT);
    pinMode(PINOS_LEDS[3], OUTPUT);
    
    digitalWrite(PINOS_LEDS[0], LOW);
    digitalWrite(PINOS_LEDS[1], LOW);
    digitalWrite(PINOS_LEDS[2], LOW);
    digitalWrite(PINOS_LEDS[3], LOW);

    Serial.begin(115200);
}

void loop() {
    if (Serial.available() > 0) {
        
        String entrada = Serial.readStringUntil('\n');
        entrada.trim();

        int posicaoPrimeiraVirgula = entrada.indexOf(',');
        int posicaoSegundaVirgula  = entrada.lastIndexOf(',');

        if (posicaoPrimeiraVirgula != -1 && posicaoSegundaVirgula != -1 && posicaoPrimeiraVirgula != posicaoSegundaVirgula) {
            
            String stringA = entrada.substring(0, posicaoPrimeiraVirgula);
            String stringB = entrada.substring(posicaoPrimeiraVirgula + 1, posicaoSegundaVirgula);
            String operacao = entrada.substring(posicaoSegundaVirgula + 1);

            int valorA = strtol(stringA.c_str(), NULL, 2);
            int valorB = strtol(stringB.c_str(), NULL, 2);

            if (operacao == "sub") {
                valorB = (~valorB) & 0x0F;
            }

            int somaProvisoria = valorA + valorB;

            int resultadoFinal = somaProvisoria;
            if (somaProvisoria > 15) {
                int bitQueSobrou = (somaProvisoria >> 4) & 0x01;
                int baseDe4Bits = somaProvisoria & 0x0F;
                resultadoFinal = baseDe4Bits + bitQueSobrou;
            }

            digitalWrite(PINOS_LEDS[0], (resultadoFinal >> 0) & 0x01);
            digitalWrite(PINOS_LEDS[1], (resultadoFinal >> 1) & 0x01); 
            digitalWrite(PINOS_LEDS[2], (resultadoFinal >> 2) & 0x01); 
            digitalWrite(PINOS_LEDS[3], (resultadoFinal >> 3) & 0x01);

            Serial.print("Operando A (Decimal): ");
            Serial.println(valorA);
            
            Serial.print("Operando B (Decimal): ");
            Serial.println(valorB);
            
            Serial.print("Resultado Final (Decimal): ");
            Serial.println(resultadoFinal);
            
            Serial.print("Estado dos LEDs (Binario): ");
            Serial.print((resultadoFinal >> 3) & 0x01);
            Serial.print((resultadoFinal >> 2) & 0x01);
            Serial.print((resultadoFinal >> 1) & 0x01);
            Serial.println((resultadoFinal >> 0) & 0x01);
            Serial.println("---------------------------------");
        }
    }
}