# 🕹️ PONG 1972 - Vintage Arcade Experience

Ein simples, cooles und authentisches Ping-Pong-Spiel im Stil der 70er Jahre (Atari Pong 1972 Hommage), programmiert mit **Pygame-CE** und **NumPy**.

---

## 🚀 Spiel starten

Du kannst das Spiel ganz einfach mit `uv` oder `python` ausführen:

```bash
# Mit uv:
uv run python pong.py

# Oder direkt als CLI-Befehl:
uv run test

# Oder mit Standard-Python (wenn Umgebung aktiv ist):
python pong.py
```

---

## 🎮 Steuerung

### Spieler-Steuerung
| Spieler | Tasten | Beschreibung |
|---|---|---|
| **Spieler 1 (Links)** | <kbd>W</kbd> / <kbd>S</kbd> | Schläger nach oben / unten |
| **Spieler 2 (Rechts)** | <kbd>▲</kbd> / <kbd>▼</kbd> | Schläger nach oben / unten (im 2-Spieler-Modus) |

### Spielmodi
- <kbd>1</kbd> : **1-Spieler-Modus** gegen die Retro-KI
- <kbd>2</kbd> : **2-Spieler-Modus** (lokal an einer Tastatur)
- <kbd>A</kbd> : **Attract Mode** (KI gegen KI Automatendemo wie in den 70er Arcades)

### Retro-Features & Einstellungen
- <kbd>C</kbd> : **Farbpalette wechseln**
  1. *Classic B&W (1972)* (Klassisches Schwarz-Weiß)
  2. *Phosphor Green (P1)* (Oszilloskop / Grün-Phosphor CRT)
  3. *Amber CRT (P3)* (Klassischer 70er Bernstein-Monitor)
  4. *Cyan Arcade* (Retro-Neonblau)
- <kbd>L</kbd> : **CRT-Scanlines** Ein- / Ausschalten
- <kbd>D</kbd> : **KI-Schwierigkeitsgrad** anpassen (*EASY*, *CLASSIC 1972*, *PRO HARD*)
- <kbd>M</kbd> : **Sound stummschalten** / aktivieren
- <kbd>SPACE</kbd> : Spiel starten / Aufschlag / Pause
- <kbd>P</kbd> : Pause
- <kbd>R</kbd> : Match zurücksetzen
- <kbd>ESC</kbd> : Hauptmenü / Beenden

---

## ✨ Features

- **Echte 70er-Jahre Physik**: Der Abprallwinkel hängt genau davon ab, an welcher Stelle der Ball den Schläger trifft (Mitte = gerade, Kanten = scharfe Winkel).
- **Beschleunigung**: Der Ball wird mit jedem Ballwechsel schrittweise schneller.
- **Retro-Grafik**:
  - Segmentiertes Netz in der Spielfeldmitte
  - Authentische 7-Segment-Digitalanzeige für Spielstände
  - Quadratischer Retro-Ball und Schläger
  - Phosphor-Nachleuchteffekt (Ball-Schweif wie bei echten Röhrenmonitoren)
  - CRT-Scanlines und Glasrand-Vignette
- **Procedurales 8-Bit-Audio**:
  - Synthetisierte Rechteckschwingungen (459 Hz Paddle-Hit, 226 Hz Wall-Hit, absteigender Buzzer bei Punktverlust, Sieges-Fanfare). Keine externen Sounddateien nötig!
- **Attract Mode**: Im Menü spielen zwei KIs im Hintergrund wie auf echten Spielhallen-Automaten von 1972.
- **Match-Ziel**: Der erste Spieler mit 11 Punkten gewinnt das Match.
