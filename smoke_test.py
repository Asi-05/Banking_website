from __future__ import annotations

from datetime import date

from src.services.account_service import account_service
from src.services.auth_service import auth_service
from src.services.budget_service import budget_service
from src.services.transaction_service import transaction_service


def expect_exception(action_name: str, fn, exc_type):
    try:
        fn()
    except exc_type as exc:
        print(f"[OK] {action_name}: erwartete Exception erhalten -> {exc}")
        return
    except Exception as exc:  # pragma: no cover - explicit smoke handling
        raise AssertionError(
            f"{action_name}: falscher Exception-Typ {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{action_name}: erwartete Exception {exc_type.__name__} blieb aus")


def main() -> None:
    print("=== SMOKE TEST START ===")

    # Login-Test: korrekte Daten
    login_ok = auth_service.login("BB-100001", "dummy_hash_1")
    assert login_ok.get("success") is True
    print(f"[OK] Login korrekt: user_id={login_ok['user_id']}")

    # Login-Test: falsches Passwort
    expect_exception(
        "Login mit falschem Passwort",
        lambda: auth_service.login("BB-100001", "falsch"),
        ValueError,
    )

    # Transaktion-Test: gueltige Einnahme mit account_id
    tx = transaction_service.create_transaction(
        {
            "amount": 150.0,
            "type": "income",
            "date": date(2026, 1, 15),
            "category_id": 10,
            "account_id": 1,
            "card_id": None,
            "creditcard_id": None,
            "note": "Smoke-Einnahme",
        }
    )
    assert tx.transaction_id is not None
    print(f"[OK] Einnahme erstellt: transaction_id={tx.transaction_id}")

    # Exactly-one-Regel provozieren: alle Quellen None
    expect_exception(
        "Exactly-one-Regel (alle Quellen None)",
        lambda: transaction_service.create_transaction(
            {
                "amount": 10.0,
                "type": "expense",
                "date": date(2026, 1, 15),
                "category_id": 10,
                "account_id": None,
                "card_id": None,
                "creditcard_id": None,
                "note": "Ungueltig",
            }
        ),
        ValueError,
    )

    # Budget-Test: erstes Budget anlegen
    budget = budget_service.set_budget(
        {
            "user_id": 1,
            "limit_amount": 500.0,
            "month": 1,
            "year": 2026,
            "category_id": 10,
        }
    )
    assert budget.budget_id is not None
    print(f"[OK] Budget erstellt: budget_id={budget.budget_id}")

    # Budget-Test: Duplikat muss Exception werfen
    expect_exception(
        "Doppeltes Budget anlegen",
        lambda: budget_service.set_budget(
            {
                "user_id": 1,
                "limit_amount": 700.0,
                "month": 1,
                "year": 2026,
                "category_id": 10,
            }
        ),
        ValueError,
    )

    # Konto-Test: Schliessen mit Balance > 0 muss fehlschlagen
    expect_exception(
        "Konto mit Balance > 0 schliessen",
        lambda: account_service.close_account(1),
        ValueError,
    )

    print("=== SMOKE TEST ERFOLGREICH ===")


if __name__ == "__main__":
    main()
