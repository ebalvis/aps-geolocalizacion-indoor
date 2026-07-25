# -*- coding: utf-8 -*-
"""
Descarga wifi_log.csv del M5StickC por USB, sin comandos.

Detecta solo el puerto del M5, se conecta y baja el archivo a esta misma carpeta
con la fecha y la hora en el nombre. Uso normal: doble clic en
descargar_wifi_log.bat (Windows). También sirve:  python descargar_wifi_log.py
"""
import sys
import subprocess
from datetime import datetime


def instalar(paquete):
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", paquete])


try:
    from serial.tools import list_ports
except ImportError:
    print("Instalando dependencias (pyserial)...")
    instalar("pyserial")
    from serial.tools import list_ports


def buscar_m5():
    """Devuelve el puerto COM del M5 (chip USB-serie CH9102/CP210x/CH340)."""
    claves = ("CH9102", "CH340", "CP210", "Silicon Labs", "USB-SERIAL",
              "USB Serial", "UART", "Espressif")
    candidatos = []
    for p in list_ports.comports():
        texto = " ".join(str(x) for x in (p.description, p.manufacturer, p.hwid))
        if any(k.lower() in texto.lower() for k in claves):
            candidatos.append(p.device)
    return candidatos


def main():
    puertos = buscar_m5()
    if not puertos:
        print("No encuentro el M5. Comprueba que:")
        print("  - está conectado por USB")
        print("  - no lo tiene abierto Thonny, UIFlow u otro programa")
        return
    if len(puertos) > 1:
        print("Hay varios dispositivos:", ", ".join(puertos))
        print("Usaré el primero:", puertos[0])
    puerto = puertos[0]

    salida = "wifi_log_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    print("M5 en {}. Descargando a {} ...".format(puerto, salida))

    # mpremote hace la copia por el puerto serie. 'resume' se engancha sin
    # reiniciar el dispositivo (así funciona aunque la app esté corriendo).
    try:
        import mpremote  # noqa: F401
    except ImportError:
        print("Instalando dependencias (mpremote)...")
        instalar("mpremote")

    r = subprocess.run([sys.executable, "-m", "mpremote", "connect", puerto,
                        "resume", "fs", "cp", ":wifi_log.csv", salida])
    if r.returncode == 0:
        print("\nDescargado correctamente:", salida)
    else:
        print("\nNo se pudo descargar. ¿El archivo existe en el M5?")
        print("En el M5, la primera vez hay que grabar algún punto (botón A).")


if __name__ == "__main__":
    main()
    try:
        input("\nPulsa Enter para cerrar.")
    except Exception:
        pass
