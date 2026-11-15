# SmartBar Didattico - Reader 🏷️💳

Firmware in **MicroPython** per il modulo lettore NFC portatile basato su **Raspberry Pi Pico 2W**, progettato come periferica hardware di campo per l'ecosistema gestionale **SmartBar Didattico**.

## 🚀 Caratteristiche Principali
* **Connettività Wi-Fi Intelligente:** Scansione automatica delle reti presenti e gestione archivio persistente.
* **Portale Captive:** Genera un Access Point (SmartBar-Reader) per configurare le credenziali Wi-Fi al primo avvio.
* **Interfaccia OLED:** Display I2C 0.96" per feedback visivo immediato.
* **Cloud Firestore:** Comunicazione REST con Firebase per il passaggio istantaneo dell'UID (
fc_reader/ultimo_scan).

## 🔌 Schema Collegamenti (Bus I2C)
* **VCC** -> Pin 36 (3V3)
* **GND** -> Pin 38 (GND)
* **SDA** -> Pin 6 (GP4)
* **SCL** -> Pin 7 (GP5)
