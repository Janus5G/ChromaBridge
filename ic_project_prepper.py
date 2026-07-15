import os
import json
import zipfile
import http.server
import socketserver
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Konfiguration
MAKS_ZIP_STRENG_MB = 14.5
MAKS_ZIP_BYTES = MAKS_ZIP_STRENG_MB * 1024 * 1024
IGNORER_MAPPER = {"scripts", ".git", ".github", "__pycache__", "node_modules", "zip_output", "test_ingestion_input", "test_binary_output"}
IGNORER_FILER = {".ds_store", "thumbs.db", "ic_project_prepper.py", "prepper_log.txt", "assets.json", "README.md", ".gitignore"}

# Wallet-format krav
WALLET_JSON = {
    "value": 0,
    "representation": "2^0 + 0",
    "source_address": "C0:F5:system:D0"
}

log_linjer = []

def log(besked: str):
    tidsstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formateret = f"[{tidsstempel}] {besked}"
    print(formateret)
    log_linjer.append(formateret)

def parse_data_fil(fil_sti: str) -> Optional[Dict[str, Any]]:
    """
    Læser en datafil og udtrækker value, representation og source_address.
    Understøtter JSON, CSV og plain text.
    """
    try:
        with open(fil_sti, 'r', encoding='utf-8') as f:
            indhold = f.read().strip()
        
        # Forsøg at parse som JSON
        try:
            data = json.loads(indhold)
            if "value" in data or "representation" in data:
                return {
                    "value": data.get("value", 0),
                    "representation": data.get("representation", f"{data.get('value', 0)}"),
                    "source_address": data.get("source_address", f"C0:F5:{os.path.basename(fil_sti).replace('.json','')}:D0"),
                    "metadata": {k: v for k, v in data.items() if k not in ["value", "representation", "source_address"]}
                }
        except json.JSONDecodeError:
            pass
        
        # Hvis det er en simpel tekstfil med et tal
        try:
            value = int(indhold)
            return {
                "value": value,
                "representation": f"2^{value.bit_length()-1} + {value - 2**(value.bit_length()-1)}",
                "source_address": f"C0:F5:{os.path.basename(fil_sti).replace('.txt','')}:D0",
                "metadata": {"file_type": "plain_text"}
            }
        except ValueError:
            pass
        
        # Hvis det er en CSV med tal
        if ',' in indhold or ';' in indhold or '\t' in indhold:
            rows = [row for row in indhold.replace(';', ',').replace('\t', ',').split('\n') if row.strip()]
            for row in rows:
                parts = row.split(',')
                if parts and parts[0].strip().isdigit():
                    value = int(parts[0].strip())
                    return {
                        "value": value,
                        "representation": f"2^{value.bit_length()-1} + {value - 2**(value.bit_length()-1)}",
                        "source_address": f"C0:F5:{os.path.basename(fil_sti).replace('.csv','')}:D0",
                        "metadata": {"file_type": "csv", "row": row}
                    }
        
        # Generer fra hash hvis alt andet fejler
        hash_val = int(hashlib.md5(indhold.encode()).hexdigest()[:8], 16) % 1000000
        return {
            "value": hash_val,
            "representation": f"2^{hash_val.bit_length()-1} + {hash_val - 2**(hash_val.bit_length()-1)}",
            "source_address": f"C0:F5:{os.path.basename(fil_sti).replace('.txt','')}:D0",
            "metadata": {"file_type": "generated_from_hash"}
        }
        
    except Exception as e:
        log(f"⚠️ Kunne ikke parse {fil_sti}: {str(e)}")
        return None

def generer_wallet_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Konverterer data til wallet-format.
    """
    value = data.get("value", 0)
    representation = data.get("representation", f"{value}")
    source_address = data.get("source_address", "C0:F5:grøn:D0")
    
    # Parse base/exponent/rest fra representation
    base, exponent, rest = parse_representation(representation, value)
    
    return {
        "payload_id": hashlib.md5(json.dumps(data).encode()).hexdigest()[:16],
        "source_address": source_address,
        "base": base,
        "exponent": exponent,
        "rest": rest,
        "value": value,
        "representation": representation,
        "ledger_proof": generate_ledger_proof(data),
        "timestamp": time.time()
    }

def parse_representation(rep: str, value: int) -> tuple:
    """Parser "base^exponent + rest" til (base, exponent, rest)."""
    if not rep:
        return 2, 0, 0
    
    rep = rep.replace(" ", "")
    rest = 0
    
    if "+" in rep:
        power_part, rest_str = rep.split("+", 1)
        try:
            rest = int(rest_str)
        except ValueError:
            rest = 0
    else:
        power_part = rep
    
    if "^" in power_part:
        base_str, exp_str = power_part.split("^", 1)
        try:
            base = int(base_str)
            exponent = int(exp_str)
        except ValueError:
            base, exponent = 2, 0
    else:
        base, exponent = find_base_exponent(value, rest)
    
    return base, exponent, rest

def find_base_exponent(value: int, rest: int = 0) -> tuple:
    target = value - rest
    if target <= 0:
        return 2, 0
    
    for base in [2, 3, 5, 7, 10]:
        exp = 0
        temp = 1
        while temp <= target:
            if temp == target:
                return base, exp
            temp *= base
            exp += 1
    
    return 2, 0

def generate_ledger_proof(data: Dict) -> List[str]:
    """Genererer ledger proofs fra data."""
    json_str = json.dumps(data, sort_keys=True).encode('utf-8')
    h1 = hashlib.sha256(json_str[:len(json_str)//2]).hexdigest()
    h2 = hashlib.sha256(json_str[len(json_str)//2:]).hexdigest()
    return [h1, h2]

def scan_og_konverter_data():
    """
    Scanner projektets mapper, konverterer data til wallet-format,
    og gemmer i test_ingestion_input/ med korrekt struktur.
    """
    log("=== Starter Data Scanning & Konvertering til Wallet-format ===")
    rod_sti = os.getcwd()
    input_mappe = os.path.join(rod_sti, "test_ingestion_input")
    
    if not os.path.exists(input_mappe):
        os.makedirs(input_mappe)
        log(f"✅ Oprettet input-mappe: {input_mappe}")
    
    total_konverteret = 0
    total_mapper = 0
    
    for element in sorted(os.listdir(rod_sti)):
        fuld_sti = os.path.join(rod_sti, element)
        
        if os.path.isdir(fuld_sti) and element.lower() not in IGNORER_MAPPER:
            log(f"📁 Behandler mappe: /{element}")
            
            # Opret undermappe i test_ingestion_input
            target_dir = os.path.join(input_mappe, element)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            # Find datafiler i mappen
            data_filer = []
            for f in os.listdir(fuld_sti):
                f_sti = os.path.join(fuld_sti, f)
                if os.path.isfile(f_sti) and f.lower() not in IGNORER_FILER:
                    data_filer.append(f_sti)
            
            if not data_filer:
                log(f"  ⚠️ Ingen filer fundet i /{element} – opretter test-data")
                # Opret test-data hvis mappen er tom
                test_data = {
                    "value": 1234567,
                    "representation": "3^12 + 703126",
                    "source_address": f"C0:F5:{element}:D0"
                }
                with open(os.path.join(target_dir, f"{element}_test.json"), 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, indent=2)
                total_konverteret += 1
                total_mapper += 1
                continue
            
            # Processér hver fil
            for fil_sti in data_filer:
                parsed = parse_data_fil(fil_sti)
                if parsed:
                    wallet_json = generer_wallet_json(parsed)
                    
                    # Gem som JSON i input-mappen
                    output_navn = os.path.basename(fil_sti)
                    if not output_navn.endswith('.json'):
                        output_navn = output_navn + '.json'
                    output_sti = os.path.join(target_dir, output_navn)
                    
                    with open(output_sti, 'w', encoding='utf-8') as f:
                        json.dump(wallet_json, f, indent=2)
                    
                    total_konverteret += 1
                    log(f"  ✅ Konverteret: {os.path.basename(fil_sti)} -> {output_navn}")
                else:
                    log(f"  ⚠️ Kunne ikke parse: {os.path.basename(fil_sti)}")
            
            total_mapper += 1
    
    log(f"\n📊 Opsummering: {total_mapper} mapper behandlet, {total_konverteret} filer konverteret.")
    log(f"📁 Data gemt i: {input_mappe}")
    log("=== Konvertering færdig ===")

def generer_manifest_og_pak():
    """Original ZIP-pakning – nu med korrekt struktur."""
    log("=== Starter Professionel IC Projekt Klargøring ===")
    rod_sti = os.getcwd()
    manifest = {}
    total_filer = 0
    
    zip_ud_mappe = os.path.join(rod_sti, "zip_output")
    if not os.path.exists(zip_ud_mappe):
        os.makedirs(zip_ud_mappe)
    
    # Scan og opret manifest
    for element in sorted(os.listdir(rod_sti)):
        fuld_sti = os.path.join(rod_sti, element)
        
        if os.path.isdir(fuld_sti) and element.lower() not in IGNORER_MAPPER:
            filer = [
                f for f in os.listdir(fuld_sti) 
                if os.path.isfile(os.path.join(fuld_sti, f)) and f.lower() not in IGNORER_FILER
            ]
            manifest[element] = sorted(filer)
            total_filer += len(filer)
            log(f"Registreret mappe: /{element} ({len(filer)} filer)")

    # Gem assets.json
    with open("assets.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log(f"Succes: 'assets.json' oprettet med {total_filer} filer.")

    # Smart ZIP-pakning
    log("Begynder intelligent ZIP-pakning (Maks 15MB pr. fil)...")
    
    for mappe, filer in manifest.items():
        if not filer:
            continue
            
        del_nummer = 1
        nuvaerende_zip_navn = os.path.join(zip_ud_mappe, f"{mappe}_del{del_nummer}.zip")
        z = zipfile.ZipFile(nuvaerende_zip_navn, 'w', zipfile.ZIP_DEFLATED)
        nuvaerende_zip_stoerrelse = 0
        pakket_i_mappe = 0
        
        for fil in filer:
            fil_sti = os.path.join(rod_sti, mappe, fil)
            fil_stoerrelse = os.path.getsize(fil_sti)
            
            if fil_stoerrelse > MAKS_ZIP_BYTES:
                log(f"  ⚠️ ADVARSEL: Enkeltfil '{fil}' er større end 15MB ({fil_stoerrelse / (1024*1024):.2f}MB)!")
            
            if nuvaerende_zip_stoerrelse + fil_stoerrelse > MAKS_ZIP_BYTES and nuvaerende_zip_stoerrelse > 0:
                z.close()
                log(f"  📦 Oprettet: /zip_output/{mappe}_del{del_nummer}.zip (~{nuvaerende_zip_stoerrelse / (1024*1024):.2f} MB)")
                del_nummer += 1
                nuvaerende_zip_navn = os.path.join(zip_ud_mappe, f"{mappe}_del{del_nummer}.zip")
                z = zipfile.ZipFile(nuvaerende_zip_navn, 'w', zipfile.ZIP_DEFLATED)
                nuvaerende_zip_stoerrelse = 0
            
            z.write(fil_sti, os.path.join(mappe, fil))
            nuvaerende_zip_stoerrelse += fil_stoerrelse
            pakket_i_mappe += 1
            
        z.close()
        log(f"  📦 Oprettet: /zip_output/{mappe}_del{del_nummer}.zip (~{nuvaerende_zip_stoerrelse / (1024*1024):.2f} MB)")
        log(f"Færdig med /{mappe}: Pakket {pakket_i_mappe} filer ind i {del_nummer} ZIP-del(e).")

    with open("prepper_log.txt", "w", encoding="utf-8") as l:
        l.write("\n".join(log_linjer) + "\n")
    log("=== Klargøring fuldført! Log gemt i 'prepper_log.txt' ===")

class SafeHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Stille logs for at undgå spam
        pass

def koer_localhost_server(port=8080):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), SafeHTTPHandler) as httpd:
        log(f"\n🚀 LOKAL TEST SERVER: Åbn http://localhost:{port}/ i din browser")
        log("Tjek at din app kører perfekt lokalt. Tryk CTRL+C for at afslutte.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            log("\nServer stoppet af udvikleren.")

if __name__ == "__main__":
    # 1. Scan og konverter data til wallet-format
    scan_og_konverter_data()
    
    # 2. Pak til IC-deployment (ZIP)
    generer_manifest_og_pak()
    
    # 3. Start lokal server til test
    koer_localhost_server()