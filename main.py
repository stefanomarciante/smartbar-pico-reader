import network
import socket
import time
import json
import urequests
import framebuf
from machine import Pin, I2C

# ==========================================
# IMPOSTA L'HOSTNAME DI RETE
# ==========================================
wlan_sta = network.WLAN(network.STA_IF)
wlan_sta.active(True)
try:
    wlan_sta.config(hostname="SmartBar-Reader")
except:
    pass

# ==========================================
# CONFIGURAZIONE FIREBASE & RETI PREDEFINITE
# ==========================================
FIREBASE_PROJECT_ID = "cassabardidattico-a8ef3"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/nfc_reader/ultimo_scan"

DEFAULT_NETWORKS = [
    {"ssid": "TIM-99243957", "password": "tfY3CuS5NSCsZGuHdCGuYtCG"},
    {"ssid": "iPhone di Stefano", "password": "i3tkudksmekni"}
]

WIFI_FILE = "wifi_networks.json"

# ==========================================
# DRIVER OLED UNIVERSALE (SSD1306 / SH1106)
# ==========================================
class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        time.sleep_ms(100)
        self.init_display()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytearray([0x80, cmd]))
        time.sleep_ms(1)

    def init_display(self):
        for cmd in (
            0xAE, 0x20, 0x02, 0xA1, 0xC8, 0xA8, self.height - 1,
            0xD3, 0x00, 0x40, 0xDA, 0x12, 0xD5, 0x80, 0xD9, 0xF1,
            0xDB, 0x30, 0x81, 0xFF, 0xA4, 0xA6, 0x8D, 0x14, 0xAF
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def show(self):
        for page in range(self.pages):
            self.write_cmd(0xB0 | page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)
            start = page * self.width
            end = start + self.width
            for i in range(start, end, 32):
                self.i2c.writeto(self.addr, b'\x40' + self.buffer[i:i+32])

# ==========================================
# INIZIALIZZAZIONE I2C STABILIZZATA
# ==========================================
Pin(4, Pin.IN, Pin.PULL_UP)
Pin(5, Pin.IN, Pin.PULL_UP)
time.sleep_ms(100)

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000, timeout=50000)
oled = SSD1306_I2C(128, 64, i2c)

def mostra_oled(riga1="", riga2="", riga3="", riga4=""):
    try:
        oled.fill(0)
        oled.text(str(riga1)[:16], 0, 0)
        oled.text(str(riga2)[:16], 0, 16)
        oled.text(str(riga3)[:16], 0, 34)
        oled.text(str(riga4)[:16], 0, 50)
        oled.show()
    except Exception as e:
        print("Avviso OLED:", e)

# ==========================================
# DRIVER PN532 I2C (ALLINEAMENTO BYTE CORRETTO)
# ==========================================
PN532_I2C_ADDR = 0x24

class PN532_I2C:
    def __init__(self, i2c_bus):
        self.i2c = i2c_bus
        self.wakeup()
        self.sam_configuration()

    def wakeup(self):
        for _ in range(3):
            try:
                self.i2c.writeto(PN532_I2C_ADDR, b'\x00')
            except:
                pass
            time.sleep_ms(50)

    def _write_frame(self, data):
        length = len(data)
        frame = bytearray([0x00, 0x00, 0xFF, length, (~length + 1) & 0xFF])
        frame.extend(data)
        checksum = (~sum(data) + 1) & 0xFF
        frame.extend([checksum, 0x00])
        self.i2c.writeto(PN532_I2C_ADDR, frame)

    def _wait_ready(self, timeout=300):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            try:
                if self.i2c.readfrom(PN532_I2C_ADDR, 1)[0] == 0x01:
                    return True
            except:
                pass
            time.sleep_ms(10)
        return False

    def _read_response(self, length, timeout=300):
        if not self._wait_ready(timeout):
            return None
        try:
            self.i2c.readfrom(PN532_I2C_ADDR, 7)
        except:
            return None
        
        if not self._wait_ready(timeout):
            return None
        try:
            raw = self.i2c.readfrom(PN532_I2C_ADDR, length + 8)
            for idx in range(len(raw) - 1):
                if raw[idx] == 0xD5:
                    return raw[idx:]
            return None
        except:
            return None

    def sam_configuration(self):
        try:
            self._write_frame([0xD4, 0x14, 0x01, 0x14, 0x01])
            self._read_response(2, 500)
        except:
            pass

    def read_passive_target(self):
        try:
            self._write_frame([0xD4, 0x4A, 0x01, 0x00])
            res = self._read_response(19, 250)
            if res and len(res) >= 7 and res[0] == 0xD5 and res[1] == 0x4B and res[2] == 0x01:
                uid_len = res[7]
                uid = res[8:8+uid_len]
                return "".join(["{:02X}".format(b) for b in uid])
        except:
            pass
        return None

# ==========================================
# GESTIONE INTELLIGENTE MEMORIA WI-FI
# ==========================================
def url_decode(s):
    s = s.replace('+', ' ')
    parti = s.split('%')
    res = parti[0]
    for p in parti[1:]:
        if len(p) >= 2:
            try:
                res += chr(int(p[:2], 16)) + p[2:]
            except:
                res += '%' + p
        else:
            res += '%' + p
    return res

def gestisci_archivio_reti(nuova_rete=None):
    archivio = {}
    for r in DEFAULT_NETWORKS:
        if r.get("ssid"):
            archivio[r["ssid"]] = r["password"]
            
    try:
        with open(WIFI_FILE, "r") as f:
            salvate = json.load(f)
            if isinstance(salvate, list):
                for r in salvate:
                    archivio[r["ssid"]] = r["password"]
            elif isinstance(salvate, dict) and "ssid" in salvate:
                archivio[salvate["ssid"]] = salvate["password"]
    except:
        pass

    if nuova_rete and nuova_rete.get("ssid"):
        archivio[nuova_rete["ssid"]] = nuova_rete["password"]

    lista_finale = [{"ssid": k, "password": v} for k, v in archivio.items()]
    try:
        with open(WIFI_FILE, "w") as f:
            json.dump(lista_finale, f)
    except:
        pass

    return archivio

def connetti_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep_ms(500)
    
    if wlan.isconnected():
        ssid_attuale = wlan.config('essid')
        return ssid_attuale if ssid_attuale else "TIM-99243957"

    reti_note = gestisci_archivio_reti()
    mostra_oled("SmartBar Reader", "Scansione WiFi", "in corso...", "")
    
    try:
        visibili = wlan.scan()
        nomi_visibili = []
        for net in visibili:
            nome = net[0].decode('utf-8', 'ignore')
            if nome and nome not in nomi_visibili:
                nomi_visibili.append(nome)
    except:
        nomi_visibili = []

    for nome_visibile in nomi_visibili:
        nome_norm = nome_visibile.replace("’", "'")
        for ssid_noto, pwd_nota in reti_note.items():
            if ssid_noto.replace("’", "'") == nome_norm:
                mostra_oled("Trovata Rete:", nome_visibile, "Connessione...", "")
                wlan.connect(nome_visibile, pwd_nota)
                for _ in range(24):
                    if wlan.isconnected():
                        return nome_visibile
                    time.sleep(0.5)
                wlan.disconnect()

    for ssid_noto, pwd_nota in reti_note.items():
        if ssid_noto not in nomi_visibili:
            mostra_oled("Provo Rete:", ssid_noto, "Attendere...", "")
            wlan.connect(ssid_noto, pwd_nota)
            for _ in range(16):
                if wlan.isconnected():
                    return ssid_noto
                time.sleep(0.5)
            wlan.disconnect()

    return None

def avvia_portale_ap():
    ap = network.WLAN(network.AP_IF)
    ap.config(essid="SmartBar-Reader", password="password123")
    ap.active(True)
    mostra_oled("WIFI NON TROVATO", "Rete: SmartBar", "Pass:password123", "Vai a 192.168.4.1")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    
    while True:
        conn, addr = s.accept()
        req = conn.recv(1024).decode('utf-8', 'ignore')
        if "GET /save?" in req:
            try:
                params = req.split("GET /save?")[1].split(" ")[0]
                coppie = dict(p.split("=") for p in params.split("&"))
                ssid = url_decode(coppie.get("s", "")).strip()
                pwd = url_decode(coppie.get("p", "")).strip()
                gestisci_archivio_reti({"ssid": ssid, "password": pwd})
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h2>Rete aggiunta in memoria! Riavvio...</h2>")
                conn.close()
                time.sleep(1)
                import machine
                machine.reset()
            except:
                pass
        
        html = """HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="font-family:sans-serif;padding:20px;text-align:center;">
        <h2>Aggiungi WiFi a SmartBar Reader</h2>
        <form action="/save" method="get">
        <input name="s" placeholder="Nome WiFi (SSID)" style="padding:10px;width:90%;margin-bottom:10px;"><br>
        <input name="p" type="password" placeholder="Password" style="padding:10px;width:90%;margin-bottom:15px;"><br>
        <button type="submit" style="padding:12px 25px;background:#0284c7;color:white;border:none;border-radius:6px;">Salva in Memoria</button>
        </form></body></html>"""
        conn.send(html)
        conn.close()

# ==========================================
# INVIO UID A FIRESTORE E VIA USB
# ==========================================
def invia_uid_cloud(uid_hex):
    mostra_oled("CARD RILEVATA!", f"UID: {uid_hex}", "Invio al Cloud..", "")
    print(f"NFC_UID:{uid_hex}")
    
    payload = {
        "fields": {
            "uid": {"stringValue": uid_hex},
            "scan_id": {"stringValue": str(time.ticks_ms())}
        }
    }
    try:
        res = urequests.patch(FIRESTORE_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
        status = res.status_code
        res.close()
        if status == 200:
            mostra_oled("CARD RILEVATA!", f"UID: {uid_hex}", "CLOUD: OK!", "Pronto fra 2s...")
            print("Inviato a Firestore (nfc_reader/ultimo_scan) con successo!")
        else:
            mostra_oled("ERRORE FIREBASE", f"Codice: {status}", "Controlla Regole", "")
            print("Errore Firestore HTTP:", status)
    except Exception as e:
        mostra_oled("ERRORE RETE", f"UID: {uid_hex}", "Verifica WiFi", "")
        print("Errore invio:", e)
    time.sleep(2)

# ==========================================
# CICLO PRINCIPALE
# ==========================================
mostra_oled("SmartBar Reader", "Avvio sistema...", "Inizializzo NFC", "")
nfc = PN532_I2C(i2c)

rete_attiva = connetti_wifi()
if not rete_attiva:
    avvia_portale_ap()

ultimo_uid = ""
ultimo_tempo = 0

mostra_oled(f"WiFi:{rete_attiva}", "----------------", "AVVICINA CHIAVE", "O CARD NFC...")

while True:
    uid = nfc.read_passive_target()
    
    if uid:
        ora = time.ticks_ms()
        if uid != ultimo_uid or time.ticks_diff(ora, ultimo_tempo) > 3000:
            ultimo_uid = uid
            ultimo_tempo = ora
            invia_uid_cloud(uid)
            mostra_oled(f"WiFi:{rete_attiva}", "----------------", "AVVICINA CHIAVE", "O CARD NFC...")
    
    time.sleep_ms(150)