"""Tests for structured runs, ticket-linked approvals, and cash safety."""

import shutil
import tempfile
from pathlib import Path

from backend import main


def test_approval_uses_database_amount_and_preserves_cash_safety() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        main.WORKING_DB = root / "working.db"
        main.AUDIT_FILE = root / "audit.json"
        shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)

        result = main.approve_payment(main.ApprovalRequest(ticket_id=102, kind="rent", ref_id=1, amount=2400, approved_by="Human reviewer"))
        assert result["ticket_status"] == "resolved"
        assert result["new_balance"] == 1000
        assert main.checking_balance()["balance"] == 1000
        assert main.list_tickets()[1]["status"] == "resolved"

        try:
            main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="invoice", ref_id=501, amount=500, approved_by="Human reviewer"))
        except Exception as exc:
            assert "match the database" in str(exc.detail)
        else:
            raise AssertionError("caller-supplied invoice amount was accepted")

        try:
            main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="invoice", ref_id=501, amount=5000, approved_by="Human reviewer"))
        except Exception as exc:
            assert "match the database" in str(exc.detail)
        else:
            raise AssertionError("caller-supplied invoice amount was accepted")

        try:
            main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="rent", ref_id=1, amount=2400, approved_by="Human reviewer"))
        except Exception as exc:
            assert "negative cash" in str(exc.detail)
        else:
            raise AssertionError("overspending approval was accepted")


def test_replenishment_requires_verified_evidence_and_matching_pricing() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        main.WORKING_DB = root / "working.db"
        main.AUDIT_FILE = root / "audit.json"
        shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)
        try:
            main.approve_replenishment(main.ReplenishmentApprovalRequest(ticket_id=101, confirmation_id=1, vendor_id=1, sku="CC-TEE-WHITE", size="S", qty=1, unit_price=8, approved_by="Human"))
        except Exception as exc:
            assert "confirmation" in str(exc.detail)
        else:
            raise AssertionError("replenishment without evidence was accepted")

        confirmation = main.record_supplier_confirmation(main.SupplierConfirmationRequest(ticket_id=101, vendor_id=1, sku="CC-TEE-WHITE", size="S", qty=1, evidence="Verified supplier response", verified_by="Human reviewer"))
        try:
            main.approve_replenishment(main.ReplenishmentApprovalRequest(ticket_id=101, confirmation_id=confirmation["confirmation_id"], vendor_id=1, sku="CC-TEE-WHITE", size="S", qty=1, unit_price=8, approved_by="Human reviewer"))
        except Exception as exc:
            assert "open invoice" in str(exc.detail)
        else:
            raise AssertionError("blocked vendor replenishment was accepted")


def test_ticket_101_purchase_approval_does_not_require_ticket_103_decision() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        main.WORKING_DB = root / "working.db"
        main.AUDIT_FILE = root / "audit.json"
        shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)
        main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="invoice", ref_id=501, amount=840, approved_by="Human reviewer"))
        confirmation = main.record_supplier_confirmation(main.SupplierConfirmationRequest(
            ticket_id=101, vendor_id=1, sku="CC-TEE-WHITE", size="S", qty=1,
            evidence="Verified supplier response", verified_by="Human reviewer",
        ))
        result = main.approve_replenishment(main.ReplenishmentApprovalRequest(
            ticket_id=101, confirmation_id=confirmation["confirmation_id"], vendor_id=1,
            sku="CC-TEE-WHITE", size="S", qty=1, unit_price=8,
            approved_by="Human reviewer",
        ))
        assert result["ticket_status"] == "resolved"
        assert result["fully_fulfilled"] is True


def test_ticket_101_reference_style_decision_resolves_without_delivery_claim() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        main.WORKING_DB = root / "working.db"
        main.AUDIT_FILE = root / "audit.json"
        shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)
        main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="invoice", ref_id=501, amount=840, approved_by="Human reviewer"))
        decision = main.record_replenishment_decision(main.ReplenishmentDecisionRequest(ticket_id=101, approved_qty=1, unit_price=8, decided_by="Human reviewer"))
        result = main.resolve_by_replenishment_decision(decision["decision_id"])
        assert result["ticket_status"] == "resolved"
        assert result["delivery_claimed"] is False
        assert main.list_tickets()[0]["status"] == "resolved"


def test_margin_calculation_uses_recorded_cost_and_flags_below_cost() -> None:
    from mcp_server.server import check_margin

    result = check_margin("CC-HOOD-NAVY", 50, 20)
    assert result["unit_cost"] == 22
    assert result["below_cost"] is False
    assert result["discount_percent"] == round((1 - 50 / 58) * 100, 2)
    assert check_margin("CC-HOOD-NAVY", 22, 20)["below_cost"] is True


def _partial_test_setup(root: Path) -> None:
    main.WORKING_DB = root / "working.db"
    main.AUDIT_FILE = root / "audit.json"
    shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)
    main.approve_payment(main.ApprovalRequest(ticket_id=101, kind="invoice", ref_id=501, amount=840, approved_by="Human reviewer"))


def test_ticket_103_partial_fulfillment_stays_open() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _partial_test_setup(root)
        decision = main.record_order_decision(main.PartialOrderDecisionRequest(
            ticket_id=103, approved_qty=4, discount_unit_price=50,
            customer_accepts_partial=True, decided_by="Human reviewer",
        ))
        confirmation = main.record_supplier_confirmation(main.SupplierConfirmationRequest(
            ticket_id=103, vendor_id=1, sku="CC-HOOD-NAVY", size="M", qty=4,
            evidence="Verified vendor record", verified_by="Human reviewer",
        ))
        result = main.approve_replenishment(main.ReplenishmentApprovalRequest(
            ticket_id=103, confirmation_id=confirmation["confirmation_id"], vendor_id=1,
            sku="CC-HOOD-NAVY", size="M", qty=4, unit_price=50,
            approved_by="Human reviewer", decision_id=decision["decision_id"],
        ))
        assert result["ticket_status"] == "open"
        assert result["fully_fulfilled"] is False
        assert main.list_tickets()[2]["status"] == "open"


def test_ticket_103_full_fulfillment_resolves() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _partial_test_setup(root)
        decision = main.record_order_decision(main.PartialOrderDecisionRequest(
            ticket_id=103, approved_qty=20, discount_unit_price=50,
            customer_accepts_partial=False, decided_by="Human reviewer",
        ))
        confirmation = main.record_supplier_confirmation(main.SupplierConfirmationRequest(
            ticket_id=103, vendor_id=1, sku="CC-HOOD-NAVY", size="M", qty=20,
            evidence="Verified vendor record", verified_by="Human reviewer",
        ))
        result = main.approve_replenishment(main.ReplenishmentApprovalRequest(
            ticket_id=103, confirmation_id=confirmation["confirmation_id"], vendor_id=1,
            sku="CC-HOOD-NAVY", size="M", qty=20, unit_price=50,
            approved_by="Human reviewer", decision_id=decision["decision_id"],
        ))
        assert result["ticket_status"] == "resolved"
        assert result["fully_fulfilled"] is True
        assert main.list_tickets()[2]["status"] == "resolved"


def test_ticket_103_accepted_partial_offer_can_resolve_without_purchase() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        main.WORKING_DB = root / "working.db"
        main.AUDIT_FILE = root / "audit.json"
        shutil.copy2(Path(__file__).parents[1] / "data" / "campus_customs.db", main.WORKING_DB)
        decision = main.record_order_decision(main.PartialOrderDecisionRequest(
            ticket_id=103, approved_qty=8, discount_unit_price=52.20,
            customer_accepts_partial=True, decided_by="Human reviewer",
        ))
        result = main.resolve_by_order_decision(decision["decision_id"])
        assert result["resolution_type"] == "accepted_partial_offer"
        assert result["delivery_claimed"] is False
        assert result["cash_change"] == 0
        assert main.list_tickets()[2]["status"] == "resolved"
        assert main.checking_balance()["balance"] == 3400
