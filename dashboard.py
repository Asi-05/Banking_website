# Wir importieren NiceGUI, damit wir eine einfache Weboberflaeche bauen koennen.
from nicegui import ui

# Diese Liste enthaelt drei ausgedachte Test-Transaktionen fuer die Tabelle.
# Jede Transaktion ist ein kleines Woerterbuch mit den drei Spaltenwerten.
transaktionen = [
    {"datum": "01.03.2026", "beschreibung": "Miete", "betrag": "-900 EUR"},
    {"datum": "05.03.2026", "beschreibung": "Supermarkt", "betrag": "-74 EUR"},
    {"datum": "09.03.2026", "beschreibung": "Tanken", "betrag": "-55 EUR"},
]

# Diese Variable merken wir uns global, damit wir spaeter auf die Tabelle zugreifen koennen.
tabelle = None

# Diese Zahl zaehlt mit, wie oft wir auf den Button geklickt haben.
# So bekommt jede neue Dummy-Zeile ein anderes Datum/Beschreibung.
zaehler_dummy = 1


# Diese Funktion wird ausgefuehrt, wenn der Button geklickt wird.
def neue_dummy_ausgabe_hinzufuegen() -> None:
    # Wir sagen Python, dass wir die globale Zaehler-Variable veraendern wollen.
    global zaehler_dummy

    # Wir bauen eine neue ausgedachte Zeile fuer die Tabelle.
    neue_zeile = {
        "datum": f"15.03.2026 (+{zaehler_dummy})",
        "beschreibung": f"Dummy-Ausgabe {zaehler_dummy}",
        "betrag": "-20 EUR",
    }

    # Wir haengen die neue Zeile an unsere bestehende Datenliste an.
    transaktionen.append(neue_zeile)

    # Wir haengen die neue Zeile auch direkt in die sichtbare Tabelle ein.
    tabelle.rows.append(neue_zeile)

    # Wir aktualisieren die Tabelle im Browser, damit die neue Zeile sofort sichtbar ist.
    tabelle.update()

    # Wir erhoehen den Zaehler fuer den naechsten Klick.
    zaehler_dummy += 1


# Diese Funktion baut die komplette einfache Dashboard-Seite auf.
def baue_dashboard() -> None:
    # Wir sagen Python, dass wir die globale Tabellen-Variable setzen werden.
    global tabelle

    # Wir setzen etwas Abstand und eine maximale Breite,
    # damit die Seite auf Desktop und Mobilgeraeten sauber aussieht.
    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-4"):
        # Das ist die grosse Ueberschrift der Seite.
        ui.label("Mein Konto").classes("text-3xl font-bold")

        # Das ist die einfache Textanzeige fuer den aktuellen Kontostand.
        ui.label("Aktueller Kontostand: 1.500 EUR").classes("text-lg")

        # Dieser Button fuehrt beim Klick unsere Funktion aus,
        # die eine neue Dummy-Ausgabe in die Tabelle eintraegt.
        ui.button("Neue Ausgabe eintragen", on_click=neue_dummy_ausgabe_hinzufuegen)

        # Diese Tabelle zeigt die Transaktionen in drei Spalten an.
        # Wir speichern die Tabelle in der globalen Variablen,
        # damit wir spaeter aus der Button-Funktion Zeilen hinzufuegen koennen.
        tabelle = ui.table(
            columns=[
                {"name": "datum", "label": "Datum", "field": "datum", "align": "left"},
                {"name": "beschreibung", "label": "Beschreibung", "field": "beschreibung", "align": "left"},
                {"name": "betrag", "label": "Betrag", "field": "betrag", "align": "right"},
            ],
            rows=transaktionen,
            row_key="datum",
        ).classes("w-full")


# Wir rufen die Funktion auf, damit das Dashboard aufgebaut wird.
baue_dashboard()

# Wir starten die NiceGUI-App.
# Wenn du diese Datei startest, oeffnet sich die Web-App im Browser.
ui.run(title="Betterbank Dashboard")
