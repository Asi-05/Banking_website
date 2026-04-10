from sqlmodel import Session, select
from src.data_access.db import engine
from src.domain.models import User  # Geht davon aus, dass dein User-Modell hier liegt
from src.utils.validators import hash_password

def upgrade_all_passwords():
    print("Starte Passwort-Migration...")
    
    with Session(engine) as session:
        # 1. Hole alle User aus der Datenbank
        users = session.exec(select(User)).all()
        updated_count = 0

        # 2. Gehe jeden User einzeln durch
        for user in users:
            # Prüfe, ob das Passwort noch unverschlüsselt ist (kein $ enthält)
            if "$" not in user.password_hash:
                print(f"Verschlüssele Passwort für: {user.first_name} {user.last_name} (Contract: {user.contract_number})")
                
                # Hashe das aktuelle Klartext-Passwort
                user.password_hash = hash_password(user.password_hash)
                session.add(user)
                updated_count += 1
        
        # 3. Speichere alle Änderungen auf einen Schlag in der Datenbank
        if updated_count > 0:
            session.commit()
            print(f"\nErfolg! {updated_count} Passwörter wurden erfolgreich gehasht.")
        else:
            print("\nFertig! Es wurden keine unverschlüsselten Passwörter gefunden.")

if __name__ == "__main__":
    upgrade_all_passwords()