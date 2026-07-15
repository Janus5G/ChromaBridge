import os
import json
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from core.ide_extension import ChromaplexIDEExtension
from core.binary_compiler import ChromaplexBinaryCompiler
from core.wallet_bridge import InternetIdentityWalletBridge

PORT = 8090

# ------------------------------- UI GENERERING -------------------------------
def generer_rent_ui():
    aktuel_sti = os.path.join(os.getcwd(), "test_ingestion_input")

    undermapper_html = ""
    if os.path.exists(aktuel_sti):
        try:
            for item in sorted(os.listdir(aktuel_sti)):
                if os.path.isdir(os.path.join(aktuel_sti, item)) and not item.startswith("."):
                    undermapper_html += "<div class='folder-row'>"
                    undermapper_html += "  <span class='folder-name'>📁 /" + item + "</span>"
                    undermapper_html += "  <div class='toggle-group'>"
                    undermapper_html += "    <label><input type='checkbox' name='secure_" + item + "' checked> 🔒 Wallet Binær (Beskyttet)</label>"
                    undermapper_html += "    <label><input type='checkbox' name='public_" + item + "'> 🌐 Public Asset (Offentlig)</label>"
                    undermapper_html += "  </div>"
                    undermapper_html += "</div>"
        except Exception as e:
            print("⚠️ UI scanning-fejl: " + str(e))

    if not undermapper_html:
        undermapper_html = "<div style='color:#ff7675; font-style:italic; font-size:13px; font-weight:bold;'>⚠️ Ingen undermapper fundet i input-mappen! Opret en undermappe (f.eks. /database) inde i 'test_ingestion_input' og læg dine JSON-filer derind, før du kører scanningen.</div>"

    html = f"""
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>ChromaBridge - Data Governance Panel</title>
    <style>
        body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; padding: 40px; margin: 0; }}
        .wrapper {{ max-width: 1200px; margin: 0 auto; }}
        .box {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .wallet-frame {{ width: 100%; height: 700px; border: 1px solid #30363d; border-radius: 8px; background: #0d1117; overflow: hidden; }}
        .wallet-frame iframe {{ width: 100%; height: 100%; border: none; }}
        input[type="text"] {{ width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #fff; font-size: 14px; box-sizing: border-box; }}
        button {{ background: #238636; color: white; border: 0; padding: 12px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 15px; width: 100%; font-size: 14px; }}
        button:hover {{ background: #2ea44f; }}
        button.secondary {{ background: #1f6feb; width: auto; padding: 8px 20px; margin-top: 0; display: inline-block; }}
        button.secondary:hover {{ background: #388bfd; }}
        .copy-btn {{ background: #1f6feb; color: white; border: 0; padding: 6px 15px; border-radius: 4px; cursor: pointer; font-size: 12px; display: inline-block; }}
        .copy-btn:hover {{ background: #388bfd; }}
        .json-box {{ background: #0d1117; padding: 15px; border: 1px solid #30363d; border-radius: 6px; font-family: monospace; font-size: 12px; color: #e6edf3; white-space: pre-wrap; max-height: 400px; overflow: auto; margin-top: 10px; }}
        .guide-box {{ background: #1c2333; border: 1px solid #30363d; border-radius: 6px; padding: 15px; margin-bottom: 15px; }}
        .guide-box ol {{ margin: 10px 0; padding-left: 20px; }}
        .guide-box li {{ margin-bottom: 8px; color: #c9d1d9; }}
        .guide-box code {{ background: #0d1117; padding: 2px 8px; border-radius: 4px; font-size: 13px; color: #58a6ff; }}
        .err-box {{ background: #2d1c1c; border: 1px solid #f85149; color: #ff7675; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 13px; white-space: pre-wrap; margin-top: 15px; }}
        .wallet-response {{ background: #0d2818; border: 1px solid #238636; color: #56d364; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 12px; margin-top: 10px; white-space: pre-wrap; }}
        .status-box {{ background: #0d2818; border: 1px solid #238636; color: #56d364; padding: 15px; border-radius: 6px; margin-top: 15px; font-weight: bold; }}
        .folder-row {{ display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px 16px; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 10px; }}
        .folder-name {{ font-weight: bold; font-size: 14px; color: #fff; }}
        .toggle-group label {{ margin-left: 15px; font-size: 13px; cursor: pointer; }}
        .section-title {{ font-size: 14px; font-weight: bold; color: #8b949e; text-transform: uppercase; margin-bottom: 15px; margin-top: 20px; border-bottom: 1px solid #21262d; padding-bottom: 5px; }}
        h3 {{ color: #58a6ff; margin-top: 0; font-size: 16px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        pre {{ background: #0d1117; padding: 15px; border: 1px solid #30363d; border-radius: 6px; height: 350px; overflow: auto; font-family: monospace; font-size: 12px; color: #e6edf3; white-space: pre-wrap; margin: 0; }}
    </style>
</head>
<body>
<div class="wrapper">
    <h2>🔮 ChromaBridge — Data Governance Panel</h2>
    <p style="color:#8b949e; font-size:14px; margin-top:0;">Enterprise-løsning til dataklassificering og udrulning til Internet Computer via caffeine.ai</p>

    <!-- ========== WALLET IFRAME ========== -->
    <div class="box">
        <h3>💎 ChromaPlex Wallet</h3>
        <div class="wallet-frame">
            <iframe 
                src="https://chromaplex-wallet-sgm.caffeine.xyz" 
                sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                loading="lazy"
            ></iframe>
        </div>
    </div>

    <!-- ========== GUIDE + DATA ========== -->
    <div class="box">
        <h3>📦 Generér og send data til wallet</h3>

        <div class="guide-box">
            <strong>📌 Sådan gemmer du data on-chain:</strong>
            <ol style="margin: 10px 0 0 20px; color: #c9d1d9;">
                <li><strong>Generér JSON</strong> – klik på knappen nedenfor.</li>
                <li><strong>Kopier JSON</strong> – brug "📋 Kopier JSON" knappen.</li>
                <li><strong>Åbn "Modtag"</strong> i walletens side herover.</li>
                <li><strong>Indsæt JSON</strong> i walletens "Modtag" side.</li>
                <li><strong>Verificér & Gem</strong> – klik på knappen i walleten.</li>
            </ol>
            <p style="margin-top: 10px; color: #8b949e; font-size: 14px;">✅ Når du gør dette, gemmes data on-chain med din principal.</p>
        </div>

        <label style="display:block; margin-bottom:8px; font-weight:bold; font-size:14px;">📁 Aktuel projekt-sti (Automatisk detekteret):</label>
        <input type="text" id="sti" value="{aktuel_sti}" readonly style="background:#21262d; color:#8b949e;">
        
        <div class="section-title">🛡️ Dataklassificering til Dataansvarlige</div>
        <div id="folder_zone">{undermapper_html}</div>
        
        <button onclick="AfviklPipeline()">⚡ Generér JSON Payload</button>
        
        <div id="error_display" style="display:none;" class="err-box"></div>
        
        <!-- JSON output -->
        <div id="json_output" style="display:none; margin-top: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span style="font-weight: bold; color: #58a6ff;">📦 Genereret JSON Payload:</span>
                <button class="copy-btn" onclick="kopierJson()">📋 Kopier JSON</button>
            </div>
            <div id="json_display" class="json-box"></div>
            <p style="color:#8b949e; font-size:13px; margin-top: 8px;">
                💡 Indsæt JSONen i walletens <strong>"Modtag"</strong> side og klik <strong>"Verificér & Gem"</strong>.
            </p>
        </div>
        
        <div id="wallet_response" style="display:none;" class="wallet-response"></div>
    </div>

    <!-- ========== OUTPUT ========== -->
    <div id="output" style="display:none;">
        <div class="box" id="status" style="color:#56d364; font-weight:bold; font-size:14px;"></div>
        <div class="grid">
            <div class="box"><h3>🤖 1. Skræddersyet, point-minimeret Caffeine.ai Prompt</h3><pre id="prompt"></pre></div>
            <div class="box"><h3>📥 2. Uforanderlig Motoko Backend (.mo)</h3><pre id="motoko"></pre></div>
        </div>
    </div>
</div>

<script>
// ==================== JAVASCRIPT ====================

// Kopier JSON til udklipsholder
window.kopierJson = function() {{
    const jsonText = document.getElementById("json_display").innerText;
    navigator.clipboard.writeText(jsonText).then(() => {{
        alert("✅ JSON kopieret til udklipsholder!");
    }}).catch(() => {{
        const textarea = document.createElement("textarea");
        textarea.value = jsonText;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        alert("✅ JSON kopieret til udklipsholder!");
    }});
}};

// Hoved-pipeline – generér JSON payload
window.AfviklPipeline = function() {{
    const sti = document.getElementById("sti").value.trim();
    const errBox = document.getElementById("error_display");
    const outputBox = document.getElementById("output");
    const jsonOutput = document.getElementById("json_output");
    const jsonDisplay = document.getElementById("json_display");

    errBox.style.display = "none";
    outputBox.style.display = "none";
    jsonOutput.style.display = "none";

    fetch("/processer", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ projekt_sti: sti }})
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
        if (data.status === "success") {{
            if (data.payload_json) {{
                jsonDisplay.innerText = data.payload_json;
                jsonOutput.style.display = "block";
            }}
            
            outputBox.style.display = "block";
            let statusText = "📊 JSON payload genereret - indsæt det i walletens Modtag side.";
            document.getElementById("status").innerText = statusText;
            document.getElementById("prompt").innerText = data.prompt;
            document.getElementById("motoko").innerText = data.motoko;
        }} else {{
            errBox.style.display = "block";
            let errMsg = "❌ FEJL: " + data.message;
            if (data.traceback) {{
                errMsg += "\\n\\n[Traceback]\\n" + data.traceback;
            }}
            errBox.innerText = errMsg;
        }}
    }}).catch(function(e) {{
        errBox.style.display = "block";
        errBox.innerText = "❌ NETVÆRKSFEJL: " + e.message;
    }});
}};
</script>
</body>
</html>"""

    return html


# ------------------------------- ØVRIGE FUNKTIONER -------------------------------
def generer_prompt(ide, binære_filer):
    if not binære_filer:
        return "SYSTEM COMMAND: Error compiling assets. No binary files available."
    fil_navne = [os.path.basename(f) for f in binære_filer]
    streams_tekst = ", ".join(fil_navne)
    
    p = "SYSTEM COMMAND: ACT AS AN ULTRA-OPTIMIZED CHROMAPLEX OS V2 DEPLOYMENT PARSER.\n"
    p += "CONTEXT: Secure data segments have been compiled into .bin streams and signed for deployment to our decentralized ChromaPlex Wallet repository located at https://chromaplex-wallet-sgm.caffeine.xyz.\n"
    p += "Target Wallet Binary Streams: " + streams_tekst + "\n\n"
    
    p += "CHROMAPLEX ENGINE DATA STRUCTURE:\n"
    p += "- Storage Architecture: 57 Facets x 5 Color Channels with depth configuration.\n"
    p += "- Encryption & Integrity: Write-once blockchain ledger with SHA-256 validation matrices.\n"
    p += "- Data Compression Protocol: Exponential representation (base^exponent + rest).\n\n"
    
    p += "BINARY STREAM STRUCTURE:\n"
    p += "- Bytes 0-3: Magic header 'CPX2'\n"
    p += "- Bytes 4-11: Timestamp (double)\n"
    p += "- Bytes 12-15: Data length (uint32)\n"
    p += "- Bytes 16+: JSON payload\n\n"
    
    p += "TASK:\n"
    p += "Write a lightweight, production-ready TypeScript/JavaScript DataView parser for index.html that:\n"
    p += "1. Asynchronously fetches the binary payload directly from chromaplex-wallet-sgm.caffeine.xyz using standard ArrayBuffers.\n"
    p += "2. Verifies the 4-byte 'CPX2' magic header signature.\n"
    p += "3. Kirurgisk udpakker byte-offsets baseret på vores krystal-ledgers extraction_hash og ledger_proof for at genskabe den oprindelige værdi.\n"
    p += "4. Extracts and validates the source_address from the payload.\n"
    p += "5. Contains an explicit fallback routing to the wallet's secure mirror if an asset fetch throws an HTTP 404 or Font-load bug.\n\n"
    
    p += "EXPECTED OUTPUT FORMAT:\n"
    p += "{\n"
    p += "  value: number,\n"
    p += "  base: number,\n"
    p += "  exponent: number,\n"
    p += "  rest: number,\n"
    p += "  extraction_hash: string,\n"
    p += "  ledger_proof: string[]\n"
    p += "}\n\n"
    
    p += "DO NOT WRITE EXPLANATIONS. OUTPUT ONLY THE RAW UNMINIFIED FRONTEND JAVASCRIPT."
    return p


def generer_motoko(ide):
    m = "// 📥 CHROMAPLEX OS V2 — MOTOKO WALLET SYNC CANISTER\n"
    m += "import Blob \"mo:base/Blob\";\n\n"
    m += "actor ChromaplexWalletBridge {\n"
    m += "    public stable var walletSyncActive : Bool = true;\n\n"
    m += "    public shared(msg) func verificerOgGemStream(stream : Blob) : async Bool {\n"
    m += "        if (stream.size() > 0) { return true; } else { return false; }\n"
    m += "    }\n"
    m += "};\n"
    return m


# ------------------------------- KERNEL PIPELINE -------------------------------
def afvikl_core_pipeline(projekt_sti):
    try:
        if not os.path.exists(projekt_sti):
            return {"status": "error", "message": f"Mappen '{projekt_sti}' findes ikke."}

        output_dir = os.path.join(os.getcwd(), "test_binary_output")
        os.makedirs(output_dir, exist_ok=True)

        ide = ChromaplexIDEExtension(projekt_sti)
        compiler = ChromaplexBinaryCompiler(output_dir)

        if not ide.importer_og_valider():
            return {"status": "error", "message": "Importering/validering mislykkedes."}

        data_attribut = "godkendte_data"
        if not hasattr(ide, data_attribut):
            if hasattr(ide, "godkedte_data"):
                data_attribut = "godkedte_data"
            else:
                return {"status": "error", "message": "Ingen godkendte data-attributter fundet."}

        godkendte_filer = getattr(ide, data_attribut)
        if not godkendte_filer:
            return {"status": "error", "message": "Ingen godkendte data fundet."}

        binære_filer = compiler.kompiler_til_bin(godkendte_filer)
        if not binære_filer:
            return {"status": "error", "message": "Kompilering producerede ingen binære filer."}

        wallet = InternetIdentityWalletBridge()
        wallet.simuler_internet_identity_login()
        
        for bin_fil in binære_filer:
            wallet.signer_og_send_bin_klynge(bin_fil)

        payloads = wallet.afslut_og_send()
        
        payload_json = None
        if payloads:
            payload_json = json.dumps(payloads[0]["payload"], indent=2)

        return {
            "status": "success",
            "filer_behandlet": len(godkendte_filer),
            "bin_filer": [os.path.basename(f) for f in binære_filer],
            "payload_json": payload_json,
            "prompt": generer_prompt(ide, binære_filer),
            "motoko": generer_motoko(ide)
        }

    except Exception as e:
        print("\n❌ [PIPELINE FEJL]: " + str(e))
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": "Intern fejl: " + str(e),
            "traceback": traceback.format_exc()
        }


# ------------------------------- HTTP HÄNDTERER -------------------------------
class ChromaplexHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            if self.path == "/" or self.path == "":
                html = generer_rent_ui()
                encoded = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                try:
                    self.wfile.write(encoded)
                    print("✅ UI sendt til klient.")
                except:
                    pass

            elif self.path == "/favicon.ico":
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.end_headers()
                self.wfile.write(b"")

            else:
                self.send_response(404)
                self.end_headers()
        except:
            pass

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8", errors="ignore")

            if self.path == "/processer":
                try:
                    data = json.loads(body)
                    p_sti = data.get("projekt_sti", "").strip()
                except:
                    params = parse_qs(body)
                    p_sti = params.get("projekt_sti", [""])[0].strip() if params.get("projekt_sti") else ""

                if not p_sti:
                    resultat = {"status": "error", "message": "Ingen projekt-sti modtaget."}
                else:
                    resultat = afvikl_core_pipeline(p_sti)

                respons_body = json.dumps(resultat)
                encoded = respons_body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print("❌ POST fejl: " + str(e))
            traceback.print_exc()
            try:
                self.send_response(500)
                self.end_headers()
            except:
                pass


# ------------------------------- SERVER START -------------------------------
def start_server():
    try:
        server = HTTPServer(("", PORT), ChromaplexHandler)
        print("\n==================================================================")
        print("🚀 CHROMAPLEX GOVERNANCE PANEL AKTIVT (PORT " + str(PORT) + ")")
        print("🔗 Gå direkte til browseren på: http://localhost:" + str(PORT))
        print("==================================================================")
        print("\n📌 SÅDAN GØR DU:")
        print("   1. Klik på 'Generér JSON Payload'.")
        print("   2. Kopier JSON'en fra boksen.")
        print("   3. Gå til walletens 'Modtag' side (iframe).")
        print("   4. Indsæt JSON'en og klik 'Verificér & Gem'.")
        print("==================================================================\n")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stoppet.")
    except Exception as e:
        print("❌ Fejl ved start af server: " + str(e))
        traceback.print_exc()


if __name__ == "__main__":
    start_server()