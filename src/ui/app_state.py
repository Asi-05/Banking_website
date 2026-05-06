"""src.ui.app_state

Diese Datei gehoert zur **UI-Schicht**.

`NiceGUI` ist event-/zustandsgetrieben: Controller und Views muessen wissen,
wer gerade eingeloggt ist, um passende Daten zu laden und Aktionen zu erlauben.

In dieser App wird dafuer ein sehr einfacher, globaler Zustand als Dictionary
verwendet.

Wichtig fuer Anfaenger:

- Dieser Zustand ist **prozessweit** (global) und nicht pro Browser-Tab isoliert.
	Fuer eine Lern-/Demo-App ist das ok; in einer echten Multi-User-Webapp wuerde
	man pro Session/Client getrennte Zustandsobjekte verwenden.
- Der Zustand wird vor allem von Auth-/UI-Controllern gesetzt und von Views
	ausgelesen.

Keys in `app_state`:

- `current_user`: optionales User-Objekt (oder `None` wenn ausgeloggt)
- `user_id`: die ID des eingeloggten Users (oder `None`)
"""

app_state: dict = {
	"current_user": None,
	"user_id": None,
}
