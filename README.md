# SmartBar Didattico - Reader 🏷️💳

Firmware in **MicroPython** per il modulo lettore NFC portatile basato su **Raspberry Pi Pico 2W**, progettato come periferica hardware di campo per l'ecosistema gestionale **SmartBar Didattico**.

Il dispositivo legge i codici UID delle chiavette o tessere NFC degli utenti (studenti, docenti, personale ATA) e li invia in tempo reale tramite Wi-Fi al database cloud **Firebase Firestore**, consentendo la registrazione di nuove tessere e la gestione delle ricariche in mobilità all'interno degli istituti scolastici.

---

## 🚀 Caratteristiche Principali
* **Connettività Wi-Fi Intelligente:** Scansione automatica delle reti presenti nell'area e gestione di un archivio multi-rete persistente (`wifi_networks.json`).
* **Portale Captive di Emergenza:** Se nessuna rete nota è disponibile, il Pico genera un Access Point Wi-Fi (`SmartBar-Reader`) con pagina web integrata per la configurazione rapida delle credenziali da smartphone o PC.
* **Interfaccia OLED in Tempo Reale:** Display I2C da 0.96" (compatibile SSD1306 / SH1106) per feedback visivo immediato sullo stato di connessione e lettura card.
* **Integrazione Cloud Firestore:** Comunicazione REST sicura con Google Firebase per il passaggio istantaneo dei dati di scansione (`nfc_reader/ultimo_scan`).
* **Hardware Ottimizzato:** Gestione del bus I2C condiviso con resistenze di pull-up e driver PN532 ottimizzato contro i timeout di comunicazione.

---

## 🛠️ Componenti Hardware
* **Microcontrollore:** Raspberry Pi Pico 2W (RP2350 con Wi-Fi integrato)
* **Lettore RFID/NFC:** Modulo PN532 (configurato in modalità **I2C**: Dip-Switch `SEL0 = ON`, `SEL1 = OFF`)
* **Display:** Mini Display OLED 0.96" I2C (4 pin: `GND, VCC, SCL, SDA`)
* **Alimentazione:** Powerbank tascabile o cavo USB-C

---

## 🔌 Schema dei Collegamenti (Bus I2C Condiviso)

| Componente | Pin Modulo | Pin Raspberry Pi Pico 2W | Pin Fisico Pico |
| :--- | :--- | :--- | :--- |
| **Alimentazione** | VCC (entrambi) | 3V3 (OUT) | Pin 36 |
| **Massa** | GND (entrambi) | GND | Pin 38 |
| **SDA (Dati)** | SDA (PN532 e OLED) | GP4 | Pin 6 |
| **SCL (Clock)** | SCL (PN532 e OLED) | GP5 | Pin 7 |

---

## 💻 Istruzioni per l'Installazione e il Flash

### 1. Preparazione del Raspberry Pi Pico 2W
1. Tieni premuto il pulsante **BOOTSEL** sul Pico 2W e collega il cavo USB al PC (la scheda apparirà come unità di memoria `RP2350`).
2. Apri **Thonny IDE**, clicca in basso a destra sulla barra di stato per configurare l'interprete e seleziona **MicroPython (Raspberry Pi Pico)**.
3. Clicca su *"Install or update MicroPython (UF2)"*, seleziona la famiglia `RP2350 (Pico 2)` e la variante `Raspberry Pi • Pico 2 W`, quindi installa il firmware.

### 2. Configurazione e Caricamento del Codice
1. Crea un nuovo file in Thonny e incolla il codice sorgente del file **`main.py`**.
2. Modifica in cima al file le credenziali delle tue reti Wi-Fi predefinite e l'ID del tuo progetto Firebase (`FIREBASE_PROJECT_ID`).
3. Salva il file direttamente sul Raspberry Pi Pico denominandolo obbligatoriamente **`main.py`** affinché si avvii in automatico ad ogni accensione.

---

## 📱 Integrazione con la Web App
Il lettore scrive l'UID rilevato all'interno della collezione Firestore dedicata:
* **Collezione:** `nfc_reader`
* **Documento:** `ultimo_scan`
* **Campi:** `uid` (stringa) e `scan_id` (timestamp).

La Web App principale (`SmartBar Didattico`) si mette in ascolto di questo documento per precompilare automaticamente i campi nelle pagine di *Registrazione Nuova Card* e *Gestione Ricariche*.

---

## 📄 Licenza
Progetto sviluppato per scopi educativi e gestionali scolastici. Tutti i diritti riservati.
