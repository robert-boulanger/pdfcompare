# Code Signing & Distribution

## macOS

### Voraussetzungen
- Apple Developer Account ($99/Jahr)
- "Developer ID Application" Zertifikat (im Keychain)

### Umgebungsvariablen

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_ID="your@email.com"
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # App-spezifisches Passwort
export APPLE_TEAM_ID="XXXXXXXXXX"             # 10-stellige Team ID
```

App-spezifisches Passwort generieren: https://appleid.apple.com/account/manage → App-Specific Passwords

### Build

```bash
./scripts/build-macos.sh
```

Ohne die Env-Variablen wird unsigned gebaut (OK fuer lokale Nutzung).

---

## Windows

### Was passiert ohne Signing?

SmartScreen blockiert oder warnt: "Windows hat Ihren PC geschuetzt". Benutzer muss "Weitere Informationen" → "Trotzdem ausfuehren" klicken.

### Zertifikat-Optionen

| Typ | Kosten | SmartScreen |
|-----|--------|-------------|
| Unsigned | Kostenlos | Dauerhafte Warnung |
| OV (Organization Validated) | ~$230-500/Jahr | Warnung bis Reputation aufgebaut (Wochen) |
| EV (Extended Validation) | ~$300-700/Jahr | Sofort vertrauenswuerdig |
| SignPath.io (OSS) | Kostenlos | OV-Zertifikat fuer Open-Source-Projekte |

**Empfehlung fuer Open Source**: Zuerst [SignPath.io](https://about.signpath.io/product/open-source) pruefen — kostenloses OV-Zertifikat fuer qualifizierte OSS-Projekte.

**Anbieter (kommerziell)**: Sectigo (~$230/Jahr), DigiCert (~$409/Jahr), SSL.com

### Konfiguration in tauri.conf.json

```json
{
  "bundle": {
    "windows": {
      "certificateThumbprint": "SHA1_THUMBPRINT_HIER",
      "digestAlgorithm": "sha256",
      "timestampUrl": "http://timestamp.comodoca.com"
    }
  }
}
```

### Schritt-fuer-Schritt (OV)

1. OV-Zertifikat kaufen (Sectigo/SSL.com), Verifikation durchlaufen
2. `.pfx`-Datei in Windows Certificate Store importieren
3. SHA-1-Thumbprint aus Certificate Manager kopieren
4. `tauri.conf.json` mit Thumbprint konfigurieren
5. `npm run build:all` → Tauri signiert automatisch

### CI/CD (GitHub Actions)

```bash
# .pfx als Base64 kodieren
certutil -encode cert.pfx cert.b64
```

Als GitHub Secret `WINDOWS_CERTIFICATE` + `WINDOWS_CERTIFICATE_PASSWORD` hinterlegen.

### Build (ohne Signing)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

---

## Quellen

- [Tauri v2: Windows Code Signing](https://v2.tauri.app/distribute/sign/windows/)
- [Tauri v2: macOS Code Signing](https://v2.tauri.app/distribute/sign/macos/)
- [SignPath.io - Free for Open Source](https://about.signpath.io/product/open-source)
