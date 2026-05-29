# Automação Residencial com ESP32

Trabalho prático da disciplina de IOT. A ideia é simular uma casa com sensores e atuadores, tudo se comunicando via MQTT e com um painel de controle no Node-RED.

---

## O que foi feito

O ESP32 lê quatro sensores (temperatura, umidade, luminosidade e gás), controla quatro atuadores (ar-condicionado, luz do quintal, alarme de gás e luz da garagem) e exibe tudo num display OLED. As leituras são publicadas via MQTT no broker HiveMQ e o Node-RED recebe esses dados em tempo real.

Além disso, os dados são gravados numa planilha do Google Sheets a cada duas horas e um alerta por e-mail é disparado quando o sensor de gás detecta nível perigoso ou a temperatura passa de 28 graus.

---

## Como rodar

### O que precisa ter instalado

- VS Code com a extensão Wokwi
- Python 3 com a biblioteca `pyserial`
- Node.js
- Node-RED com o pacote `node-red-dashboard`

### Passo a passo

1. Abre o projeto no VS Code e inicia a simulacao pelo Wokwi (F1 > Wokwi: Start Simulator)

2. Com o simulador rodando, faz o upload dos arquivos para o ESP32 virtual:
   ```
   python upload.py
   ```

3. Inicia o Node-RED:
   ```
   node-red
   ```

4. Acessa `http://localhost:1880`, importa o arquivo `nodered_flow.json` e clica em Deploy

5. O painel fica disponivel em `http://localhost:1880/ui`

---

## Estrutura do projeto

```
main.py          - codigo principal do ESP32
boot.py          - executa no boot, lista arquivos e limpa memoria
ssd1306.py       - driver do display OLED
umqtt/simple.py  - biblioteca MQTT para MicroPython
upload.py        - script para enviar os arquivos ao ESP32 via serial
nodered_flow.json - fluxo do Node-RED com dashboard e automacoes
wokwi.toml       - configuracao do simulador
mosquitto.conf   - configuracao do broker local (usado nos testes)
```

---

## Topicos MQTT

Os sensores publicam em `home/julio/sensor/` e os comandos chegam em `home/julio/cmd/`.

| Topico | Descricao |
|--------|-----------|
| home/julio/sensor/temperature | Temperatura em graus Celsius |
| home/julio/sensor/humidity | Umidade relativa em porcentagem |
| home/julio/sensor/ldr | Luminosidade (valor bruto do ADC) |
| home/julio/sensor/gas | Gas MQ-2 (valor bruto ou "ALERTA") |
| home/julio/sensor/motion | Presenca detectada pelo PIR (ON/OFF) |
| home/julio/cmd/ac | Comando para o ar-condicionado |
| home/julio/cmd/quintal | Comando para a luz do quintal |
| home/julio/cmd/gas_alert | Comando para o alarme de gas |
| home/julio/cmd/garagem | Comando para a luz da garagem |

---

## Logica automatica

O ESP32 toma algumas decisoes sozinho, sem precisar de comando manual:

- Liga o ar-condicionado se a temperatura passar de 28 graus
- Liga a luz do quintal se a luminosidade cair abaixo de 1000 (escuro)
- Aciona o alarme de gas se o MQ-2 passar de 2000 ou o sensor digital disparar
- Liga a luz da garagem quando o PIR detecta movimento

---

## Dependencias do Node-RED

Para instalar os pacotes necessarios, dentro da pasta do Node-RED:

```
npm install node-red-dashboard
npm install node-red-node-email
```

---

## Observacoes

O broker usado e o HiveMQ publico (`broker.hivemq.com:1883`). Nao requer autenticacao mas pode ter instabilidade ocasional por ser compartilhado.

Para o envio de e-mail funcionar e necessario configurar uma senha de aplicativo do Gmail no no "Gmail Alerta" dentro do Node-RED.

O Google Sheets e alimentado via Google Apps Script. O script precisa estar vinculado a uma planilha e implantado como App da Web com acesso para qualquer pessoa.
