"""src.ui.app_state

Diese Datei gehoert zur **UI-Schicht**.

=== WAS IST DER APP-STATE? ===
`app_state` ist ein globales Python-Dictionary, das speichert, wer gerade
eingeloggt ist. Es ist die "Kommunikationsbruecke" zwischen Login-View
und allen anderen Views.

=== WARUM BRAUCHT MAN DAS? ===
NiceGUI-Views sind Python-Funktionen, die bei jedem Seitenaufruf neu
ausgefuehrt werden. Die Views muessen wissen:
    - Ist jemand eingeloggt?
    - Wer ist es? (user_id → fuer Datenbankabfragen)

Ohne `app_state` wuerden alle Views nur "leere" Seiten zeigen.

=== LOGIN-ABLAUF MIT APP_STATE ===
    1. User gibt Vertragsnummer + Passwort ein (login_view.py).
    2. AuthController.login() wird aufgerufen.
    3. Bei Erfolg setzt die View:
       app_state["user_id"] = result["user_id"]     # z.B. 1
       app_state["current_user"] = result           # das ganze Login-Ergebnis-Dict
    4. ui.navigate.to("/dashboard") → Dashboard-View wird geladen.
    5. Dashboard-View prueft:
       if app_state.get("current_user") is None:    # kein User eingeloggt?
           ui.navigate.to("/")                      # zurueck zum Login!
           return

=== LOGOUT-ABLAUF ===
    app_state["current_user"] = None
    app_state["user_id"] = None
    → Alle Views pruefen nun None und leiten zurueck zum Login.

=== KEYS IM APP_STATE ===
    "current_user":
        None → niemand eingeloggt
        dict → Login-Ergebnis (success, auth_token, user_id, executed_recurring, ...)

    "user_id":
        None → niemand eingeloggt
        int  → Datenbank-ID des eingeloggten Users (z.B. 1)
        Wird fuer alle Datenbankabfragen als Filter verwendet.

=== WICHTIGER HINWEIS ZUR SICHERHEIT ===
In dieser Demo-App ist `app_state` ein GLOBALES Dictionary.
Das bedeutet: ALLE Browser-Tabs und ALLE Benutzer teilen sich
denselben Zustand (solange sie auf dem gleichen Server-Prozess laufen).

In einer echten Multi-User-Webanwendung wuerde man:
    - Pro Browser-Session einen eigenen Zustand verwenden
    - NiceGUI's `ui.context` oder `storage.user` nutzen
    - JWT-Tokens pro Client verwalten

Fuer diese Lern-/Demo-App ist der globale Ansatz vereinfacht und akzeptabel.
"""

# Globaler Zustand: wird von allen Views gelesen und von auth_controller beschrieben.
# Initialisierung mit None = niemand eingeloggt beim App-Start.
app_state: dict = {
    # current_user: None oder Login-Ergebnis-Dict (von auth_controller.login)
    "current_user": None,
    # user_id: None oder int (Datenbank-ID des eingeloggten Users)
    "user_id": None,
    # show_logout_message: True → Login-Seite soll "Erfolgreich abgemeldet" anzeigen.
    # Wird von auth_controller.logout() auf True gesetzt und von login_view nach
    # der Anzeige sofort wieder auf False zurueckgesetzt (einmalige Meldung).
    "show_logout_message": False,
}
