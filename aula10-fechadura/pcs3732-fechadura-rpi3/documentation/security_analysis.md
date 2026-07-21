# Análise de Segurança da Fechadura Eletrônica (Raspberry Pi 3)

## Introdução
Esta análise técnica avalia o projeto da Fechadura Eletrônica baseada em Raspberry Pi 3 e kit Freenove FNK0054, com foco em identificar vulnerabilidades inerentes à arquitetura de hardware e software utilizada, bem como propor mitigações pertinentes. O sistema é composto por um teclado matricial para entrada de senha, um display LCD I2C para feedback, um buzzer e um sensor ultrassônico (HC-SR04) para verificar o estado físico da porta.

## 1. Vulnerabilidades de Hardware e Físicas

### 1.1 Tampering Físico (Violação do Sensor)
**Descrição:** O sensor ultrassônico (HC-SR04) é utilizado para monitorar se a porta está fechada (distância < 10cm). Se um atacante obtiver acesso físico à fiação do sensor ou puder inserir um objeto (como um pedaço de papelão) diretamente na frente do sensor pelo lado de fora da porta, ele pode forçar o estado lógico "FECHADO" continuamente.
**Impacto:** O Raspberry Pi continuará processando o estado como seguro ("trancado"), permitindo que a porta seja fisicamente arrombada ou aberta sem que o alarme (buzzer) seja acionado. O sistema lógico é ignorado.
**Mitigação:** 
- Instalação do sensor em local protegido e inacessível do lado externo.
- Adição de sensores redundantes com princípios físicos diferentes (ex: sensor magnético *reed switch* + sensor ultrassônico).
- *Tamper switches* na caixa do Raspberry Pi que disparem o alarme se a carcaça for aberta.

### 1.2 Interceptação de Barramento I2C
**Descrição:** O display LCD utiliza o protocolo I2C. Como o I2C é um barramento de comunicação não criptografado, um atacante com acesso físico aos fios SDA/SCL pode conectar um analisador lógico ou um microcontrolador malicioso.
**Impacto:** O atacante pode ler as mensagens enviadas ao display (vazando informações de status) ou, pior, injetar comandos no barramento I2C para corromper o display ou causar negação de serviço (DoS) no controlador I2C do Raspberry Pi.
**Mitigação:** Restrição estrita de acesso físico aos cabos. Em aplicações de alta segurança, utilizar displays com protocolos criptografados ou resinar as conexões I2C.

## 2. Vulnerabilidades de Software (Raspberry Pi 3 vs Microcontroladores)

### 2.1 Timing Attacks (Ataques de Temporização)
**Descrição:** O Raspberry Pi 3 roda um Sistema Operacional completo (Linux). O agendador de processos (*scheduler*) do Linux não é determinístico (não é um RTOS). 
**Impacto:** O tempo de processamento da senha pode variar de acordo com a carga da CPU. Um atacante sofisticado poderia medir essas pequenas variações de tempo (Timing Attacks) para deduzir caracteres da senha (se a comparação falhar precocemente no primeiro caractere incorreto, por exemplo).
**Mitigação:** Implementar a comparação de senhas em tempo constante (utilizando `hmac.compare_digest` do Python ou funções de hash criptográfico equivalentes) em vez de comparações normais de string (`==`).

### 2.2 Superfície de Ataque do SO Completo
**Descrição:** Um Raspberry Pi possui conectividade de rede (Wi-Fi/Ethernet) e serviços rodando em background (SSH, processos do sistema).
**Impacto:** Se o Raspberry Pi estiver conectado a uma rede, um atacante pode tentar invadir o sistema operacional via SSH (ataque de força bruta) ou explorar vulnerabilidades no kernel Linux. Se obtiver root, ele pode enviar comandos diretamente para os pinos GPIO e abrir a fechadura via software.
**Mitigação:** 
- Desativar serviços de rede desnecessários (ou não conectar à rede, se a fechadura for offline).
- Alterar as credenciais padrão do Raspberry Pi (`pi` / `raspberry`).
- Comparação arquitetural: Diferente de um microcontrolador dedicado como o ESP32, que executa apenas o firmware da fechadura reduzindo drasticamente a superfície de ataque remota, o RPi exige hardening a nível de SO.

## 3. Vulnerabilidades de Lógica da Fechadura

### 3.1 Força Bruta no Teclado
**Descrição:** O atacante pode tentar adivinhar a senha de 4 a 8 dígitos inserindo sequências aleatórias no teclado matricial de forma contínua.
**Impacto:** Descoberta da senha e acesso indevido.
**Mitigação (Já Implementada):** A máquina de estados possui um requisito não funcional (RNF1) implementado que aplica um bloqueio temporário (Cooldown) de 10 segundos após 3 tentativas incorretas consecutivas. Isso torna o ataque de força bruta manual matematicamente inviável (ex: tentar 10.000 combinações demoraria semanas).

## Conclusão
A arquitetura implementada resolve os requisitos funcionais estabelecidos para o protótipo. No entanto, para um produto de prateleira voltado para segurança física, o Raspberry Pi apresenta desafios devido à sua vasta superfície de ataque em nível de SO. As mitigações físicas (contra *spoofing* do sensor) e lógicas (proteção contra força bruta e comparação de senhas) são essenciais para elevar a resiliência deste sistema embarcado.
