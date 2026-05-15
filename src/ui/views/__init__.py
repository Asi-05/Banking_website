"""src.ui.views

Dieses Package enthaelt die **View-Schicht** der Anwendung (NiceGUI-Seiten).

In diesem Projekt ist die UI grob so aufgebaut:

- `views`: Rendern von Seiten/Komponenten und UI-Interaktionen
- `controllers`: Schnittstelle zwischen Views und Services, inkl. einfacher Fehlerbehandlung
- `services`: Fachlogik und Orchestrierung
- `data_access`: Datenbankzugriff ueber Repositories

Die Views werden in `src/__main__.py` als Routen registriert.
"""
