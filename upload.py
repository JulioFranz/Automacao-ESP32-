import serial
import time
import base64
import os

HOST  = "localhost"
PORT  = 4000
BAUD  = 115200
CHUNK = 64  


def _run(ser, cmd, timeout_s=15):
    """Envia comando e espera os dois \\x04 que marcam fim da execução no raw REPL."""
    ser.write(cmd if isinstance(cmd, bytes) else cmd.encode())
    ser.write(b"\x04")

    deadline = time.time() + timeout_s
    buf = bytearray()
    eot = 0

    while time.time() < deadline:
        n = ser.in_waiting
        if n:
            data = ser.read(n)
            for b in data:
                if b == 0x04:
                    eot += 1
                else:
                    buf.append(b)
            if eot >= 2:
                text = bytes(buf)
                if b"Traceback" in text or b"SyntaxError" in text or b"ValueError" in text:
                    print(f"    Erro ESP32: {text.decode(errors='replace').strip()}")
                    return False
                return True
        time.sleep(0.01)

    print(f"    Timeout. Buffer: {bytes(buf)!r}")
    return False


def entrar_raw_repl(ser):
    print("Sincronizando com MicroPython...")
    for _ in range(5):
        ser.write(b"\x03")
        time.sleep(0.1)
    ser.write(b"\r\n")
    time.sleep(0.3)
    while ser.in_waiting:
        ser.read(ser.in_waiting)

    print("Enviando Ctrl+A (raw REPL)...")
    ser.write(b"\x01")
    time.sleep(0.6)
    resp = bytearray()
    while ser.in_waiting:
        resp.extend(ser.read(ser.in_waiting))
        time.sleep(0.05)

    if b"raw REPL" in resp:
        return True

    print("Tentativa 2: soft reset + Ctrl+A...")
    ser.write(b"\x04")
    time.sleep(1.2)
    for _ in range(3):
        ser.write(b"\x03")
        time.sleep(0.1)
    ser.write(b"\x01")
    time.sleep(0.6)
    resp = bytearray()
    while ser.in_waiting:
        resp.extend(ser.read(ser.in_waiting))
        time.sleep(0.05)
    return b"raw REPL" in resp


def criar_dir(ser, nome):
    print(f"  Criando diretório '{nome}'...")
    cmd = (
        f"import os\n"
        f"try:\n    os.mkdir('{nome}')\nexcept OSError:\n    pass\n"
        f"print('OK')\n"
    )
    return _run(ser, cmd)


def enviar_arquivo(ser, nome):
    if not os.path.exists(nome):
        print(f"  Arquivo não encontrado: {nome}")
        return False

    with open(nome, "rb") as f:
        dados = f.read()

    nome_esp = nome.replace("\\", "/")
    total_chunks = (len(dados) + CHUNK - 1) // CHUNK
    print(f"  Enviando {nome_esp} ({len(dados)} bytes, {total_chunks} chunks)...")

    if not _run(ser, f"import ubinascii\nf=open('{nome_esp}','wb')\nprint('OK')\n"):
        print(f"  Erro ao abrir {nome_esp} no ESP32")
        return False

    for n, i in enumerate(range(0, len(dados), CHUNK)):
        chunk = dados[i:i + CHUNK]
        b64   = base64.b64encode(chunk).decode()
        cmd   = f"f.write(ubinascii.a2b_base64('{b64}'))\nprint('OK')\n"
        if not _run(ser, cmd):
            print(f"  Falhou no chunk {n + 1}/{total_chunks}")
            _run(ser, "try:\n    f.close()\nexcept:    pass\nprint('OK')\n")
            return False
        if (n + 1) % 20 == 0:
            print(f"    {n + 1}/{total_chunks}")

    if not _run(ser, "f.close()\nprint('OK')\n"):
        return False

    print(f"  {nome_esp} gravado com sucesso.")
    return True


try:
    print(f"Conectando a rfc2217://{HOST}:{PORT}...\n")
    ser = serial.serial_for_url(
        f"rfc2217://{HOST}:{PORT}?ign_set_control",
        baudrate=BAUD, timeout=2
    )

    if not entrar_raw_repl(ser):
        print("\nERRO: ESP32 não entrou no raw REPL.")
        print("Tente F1 → 'Wokwi: Reset Simulator' e rode de novo.")
        ser.close()
        raise SystemExit(1)

    print("Raw REPL ativo!\n")

    ok = True
    ok = ok and enviar_arquivo(ser, "boot.py")
    ok = ok and enviar_arquivo(ser, "ssd1306.py")
    ok = ok and criar_dir(ser, "umqtt")
    ok = ok and enviar_arquivo(ser, "umqtt/simple.py")
    ok = ok and enviar_arquivo(ser, "main.py")

    if ok:
        print("\nTodos os arquivos enviados com sucesso!")
    else:
        print("\nUpload terminou com erros — verifique as mensagens acima.")

    print("Reiniciando ESP32...")
    ser.write(b"\x02")   # Ctrl+B pra sai do raw REPL
    time.sleep(0.3)
    ser.write(b"\x04")   # Ctrl+D pra dar soft reboot
    time.sleep(0.5)

    ser.close()
    print("Pronto.")

except SystemExit:
    pass
except Exception as e:
    print(f"Erro: {e}")
