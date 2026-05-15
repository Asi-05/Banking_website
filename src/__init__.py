"""src

Dieses Verzeichnis ist das **Haupt-Python-Paket** der BetterBank-App.

Die Unterpakete sind nach Schichten organisiert:

- `domain`: Datenmodelle/DTOs
- `data_access`: DB-Engine, Seeding, Repositories
- `services`: Fachlogik und Orchestrierung
- `ui`: NiceGUI-Views, Controller und globaler UI-State
- `utils`: kleine Hilfsfunktionen (Validierung/Formatierung)

Das Paket selbst exportiert bewusst keine "Top-Level"-Shortcuts, damit Imports
explizit und fuer Anfaenger nachvollziehbar bleiben.
"""

