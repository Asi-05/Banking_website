"""src.ui.controllers.user_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS MACHT DIESER CONTROLLER? ===
Verbindet die Profil-Seite (in anderen Views eingebettet) mit dem UserService.

Nutzer koennen ihr Profil anpassen:
    - Telefonnummer aendern oder setzen
    - Adresse aendern oder setzen

Passwort und Vertragsnummer koennen NICHT geaendert werden (Design-Entscheidung,
da dies eine Demo-App ist).

=== AUFRUF-KETTE (Profil laden) ===
    [1] Eine View (z.B. dashboard_view oder account_view) zeigt Profil-Daten an
    [2] view ruft user_controller.get_profile(user_id) auf
    [3] user_controller ruft user_service.get_profile(user_id) auf
    [4] user_service ruft user_repository.get_by_id(user_id) auf → Datenbank
    [5] Rueckgabe: User-Objekt mit .first_name, .last_name, .phone, .address

=== AUFRUF-KETTE (Profil speichern) ===
    [1] Nutzer klickt "Speichern" nach Telefon/Adresse-Aenderung
    [2] view ruft user_controller.update_profile(user_id, phone, address) auf
    [3] user_controller ruft user_service.update_profile(...) auf
    [4] user_service aktualisiert User-Objekt und speichert via user_repository → Datenbank

=== RUECKGABEWERTE ===
    get_profile:    User-Objekt (SQLModel) oder Fehlermeldung als String
    update_profile: None (Erfolg) oder Fehlermeldung als String
"""

from src.services.user_service import user_service


class UserController:
    """UI-Controller fuer Profil-Operationen (Anzeigen und Bearbeiten).

    Delegiert alle Datenzugriffe an den UserService.
    Gibt entweder das Ergebnis (User-Objekt) oder eine Fehlermeldung als String zurueck.
    """

    def get_profile(self, user_id: int):
        """Laedt das Profil des eingeloggten Users aus der Datenbank.

        AUFRUF-KETTE:
            View (Profil-Abschnitt anzeigen) → get_profile(user_id)
            → user_service.get_profile(user_id)
            → user_repository.get_by_id(user_id) → Datenbank

        RÜCKGABE:
            User-Objekt (SQLModel-Instanz) mit Feldern:
            .user_id, .first_name, .last_name, .contract_number, .phone, .address
            (password_hash wird NICHT angezeigt - bleibt intern)

        WAS DIE VIEW DAMIT MACHT:
            result = user_controller.get_profile(user_id)
            if isinstance(result, str):
                error_label.set_text(result)  # Fehlermeldung anzeigen
            else:
                name_label.set_text(f"{result.first_name} {result.last_name}")
                phone_input.set_value(result.phone or "")

        Args:
            user_id: ID des eingeloggten Users (aus app_state["user_id"]).

        Returns:
            User-Objekt bei Erfolg, Fehlermeldung als String bei Fehler.
        """
        try:
            return user_service.get_profile(user_id)
        except Exception as e:
            return str(e)

    def update_profile(self, user_id: int, phone: str | None, address: str | None) -> str | None:
        """Aktualisiert Telefonnummer und/oder Adresse des Users.

        AUFRUF-KETTE:
            View (Button "Speichern") → update_profile(user_id, phone, address)
            → user_service.update_profile(user_id, phone, address)
            → user_repository.save(user) → Datenbank

        HINWEIS:
            Wenn phone=None uebergeben wird, bleibt die Telefonnummer unveraendert.
            Wenn address=None uebergeben wird, bleibt die Adresse unveraendert.
            Nur Felder mit einem Wert werden aktualisiert.

        WAS DIE VIEW DAMIT MACHT:
            error = user_controller.update_profile(user_id, phone_input.value, address_input.value)
            if error:
                ui.notify(error, type="negative")
            else:
                ui.notify("Profil gespeichert", type="positive")

        Args:
            user_id: ID des eingeloggten Users.
            phone: Neue Telefonnummer als String oder None (unveraendert lassen).
            address: Neue Adresse als String oder None (unveraendert lassen).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            user_service.update_profile(user_id, phone, address)
            return None
        except Exception as e:
            return str(e)


# Singleton-Instanz: wird von Views importiert, die Profil-Daten anzeigen/bearbeiten.
user_controller = UserController()
