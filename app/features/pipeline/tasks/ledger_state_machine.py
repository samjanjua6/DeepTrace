"""
Cross-Page Financial Ledger State Machine.

Maintains running balances seamlessly across multi-page bank statements.
Enforces the fundamental invariants:
  1. Opening / Brought Forward balance on Page N strictly equals Terminal / Carried Forward balance on Page N-1 (tol <= 0.01 PKR).
  2. Carried Forward balance on Page N-1 strictly equals the running balance after the final transaction on Page N-1.
  3. Continuous carryforward across page boundaries without explicit Brought Forward lines (seamless carryforward).
  4. Final ledger balance strictly equals stated closing balance in header.
  5. Macro summary balance identity: Stated Opening + Total Credits - Total Debits == Stated Closing.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PageLedgerRecord:
    page_num: int
    opening_balance: Optional[Decimal] = None
    opening_type: str = "NONE"  # "EXPLICIT_PAGE_OPENING", "EXPLICIT_BROUGHT_FORWARD", "SEAMLESS_CARRYFORWARD", "IMPLIED_ORIGIN"
    closing_balance: Optional[Decimal] = None
    closing_type: str = "NONE"  # "EXPLICIT_CARRIED_FORWARD", "TERMINAL_TRANSACTION"
    tx_count: int = 0
    total_credits: Decimal = Decimal("0.00")
    total_debits: Decimal = Decimal("0.00")
    has_discontinuity: bool = False
    discontinuity_amount: Optional[Decimal] = None


class CrossPageLedgerStateMachine:
    """
    Deterministic state machine for multi-page bank statement ledger reconciliation.
    """

    def __init__(
        self,
        stated_opening: Optional[Decimal] = None,
        stated_closing: Optional[Decimal] = None,
        stated_credits: Optional[Decimal] = None,
        stated_debits: Optional[Decimal] = None,
        tolerance: Decimal = Decimal("0.01"),
    ):
        self.stated_opening = stated_opening
        self.stated_closing = stated_closing
        self.stated_credits = stated_credits
        self.stated_debits = stated_debits
        self.tolerance = tolerance

        self.current_page: Optional[int] = None
        self.running_balance: Optional[Decimal] = stated_opening
        self.last_page_closing_balance: Optional[Decimal] = None

        self.first_transaction_processed: bool = False
        self.page_first_row_processed: bool = False
        self.implied_opening: Optional[Decimal] = None

        self.pages: dict[int, PageLedgerRecord] = {}
        self.all_ledger_rows: list[dict[str, Any]] = []
        self.discontinuities: list[dict[str, Any]] = []

    def start_page(self, page_num: int) -> None:
        """Initialize tracking for a new page in the document."""
        self.current_page = page_num
        self.page_first_row_processed = False
        if page_num not in self.pages:
            self.pages[page_num] = PageLedgerRecord(page_num=page_num)

    def process_opening_row(
        self,
        page_num: int,
        amount: Decimal,
        raw_line: str = "",
        bbox: Any = None,
    ) -> Optional[dict[str, Any]]:
        """
        Handle an explicit 'Opening Balance' row.
        - On Page 1 (or before first transaction): sets ledger origin and checks vs stated opening in header.
        - On Page N > 1: treated as an explicit Brought Forward row and verified against Page N-1 closing balance.
        """
        finding = None

        if not self.first_transaction_processed:
            # Document-level initial opening row (Page 1)
            self.running_balance = amount
            self.first_transaction_processed = True
            self.implied_opening = amount

            if page_num in self.pages:
                self.pages[page_num].opening_balance = amount
                self.pages[page_num].opening_type = "EXPLICIT_PAGE_OPENING"

            if self.stated_opening is not None and abs(amount - self.stated_opening) > self.tolerance:
                discrepancy = amount - self.stated_opening
                finding = {
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL" if abs(discrepancy) > Decimal("1000") else "HIGH",
                    "rule_id": "RULE_PK_OPENING_BALANCE_MISMATCH",
                    "risk_points": 50 if abs(discrepancy) > Decimal("1000") else 30,
                    "title": f"Opening Balance Tampering Detected (+{discrepancy:,.2f} PKR Discrepancy)" if discrepancy > 0 else f"Opening Balance Mismatch ({discrepancy:+,.2f} PKR)",
                    "description": (
                        f"Document header states Opening Balance of PKR {self.stated_opening:,.2f}, "
                        f"but transaction table starts with PKR {amount:,.2f}. "
                        f"Discrepancy: PKR {discrepancy:+,.2f}. This indicates ledger origin manipulation."
                    ),
                    "expected_value": f"PKR {self.stated_opening:,.2f}",
                    "actual_value": f"PKR {amount:,.2f}",
                    "discrepancy": f"PKR {discrepancy:+,.2f}",
                    "technical_details": {
                        "stated_opening": str(self.stated_opening),
                        "table_opening": str(amount),
                        "discrepancy": str(discrepancy),
                        "page_number": page_num,
                    },
                    "label": "Ledger Opening Row",
                    "color": "#f59e0b",
                    "page_number": page_num,
                }

            self.all_ledger_rows.append({
                "date": raw_line[:11].strip() if raw_line else "—",
                "particulars": "Opening Balance",
                "debit": None,
                "credit": None,
                "expectedBalance": float(self.stated_opening if self.stated_opening is not None else amount),
                "recordedBalance": float(amount),
                "discrepancy": float(amount - (self.stated_opening or amount)),
                "isTampered": finding is not None,
                "pageNumber": page_num,
                "rowType": "OPENING",
            })
            return finding

        else:
            # Secondary Opening row on Page N > 1 -> Treated as Brought Forward from Page N-1
            return self.process_brought_forward(page_num, amount, raw_line=raw_line, bbox=bbox, row_label="Opening Balance")

    def process_brought_forward(
        self,
        page_num: int,
        amount: Decimal,
        raw_line: str = "",
        bbox: Any = None,
        row_label: str = "Balance Brought Forward",
    ) -> Optional[dict[str, Any]]:
        """
        Handle a Brought Forward row at the top of Page N (N > 1).
        Enforces: BF_N == Closing_{N-1} (+- tolerance).
        """
        finding = None
        expected = self.last_page_closing_balance

        if expected is not None and abs(amount - expected) > self.tolerance:
            discrepancy = amount - expected
            if page_num in self.pages:
                self.pages[page_num].has_discontinuity = True
                self.pages[page_num].discontinuity_amount = discrepancy

            finding = {
                "category": "MATHEMATICAL_MISMATCH",
                "severity": "CRITICAL",
                "rule_id": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                "risk_points": 50,
                "title": f"Multi-Page Balance Discontinuity on Page {page_num}",
                "description": (
                    f"Page {page_num - 1} concluded with a balance of PKR {expected:,.2f}, "
                    f"but Page {page_num} states Brought Forward balance of PKR {amount:,.2f}. "
                    f"Discrepancy across page boundary: PKR {discrepancy:+,.2f}. This indicates inter-page balance manipulation."
                ),
                "expected_value": f"PKR {expected:,.2f}",
                "actual_value": f"PKR {amount:,.2f}",
                "discrepancy": f"PKR {discrepancy:+,.2f}",
                "technical_details": {
                    "previous_page_closing": str(expected),
                    "brought_forward_balance": str(amount),
                    "discrepancy": str(discrepancy),
                    "page_number": page_num,
                    "row_label": row_label,
                },
                "label": "Page Discontinuity",
                "color": "#dc2626",
                "page_number": page_num,
            }
            self.discontinuities.append(finding)

        self.running_balance = amount
        if page_num in self.pages:
            self.pages[page_num].opening_balance = amount
            self.pages[page_num].opening_type = "EXPLICIT_BROUGHT_FORWARD"

        self.all_ledger_rows.append({
            "date": raw_line[:11].strip() if raw_line else "—",
            "particulars": row_label,
            "debit": None,
            "credit": None,
            "expectedBalance": float(expected if expected is not None else amount),
            "recordedBalance": float(amount),
            "discrepancy": float(amount - (expected or amount)),
            "isTampered": finding is not None,
            "pageNumber": page_num,
            "rowType": "BROUGHT_FORWARD",
        })
        return finding

    def process_carried_forward(
        self,
        page_num: int,
        amount: Decimal,
        raw_line: str = "",
        bbox: Any = None,
    ) -> Optional[dict[str, Any]]:
        """
        Handle a Carried Forward row at the bottom of Page N.
        Enforces: CF_N == running_balance (+- tolerance).
        """
        finding = None
        expected = self.running_balance

        if expected is not None and abs(amount - expected) > self.tolerance:
            discrepancy = amount - expected
            if page_num in self.pages:
                self.pages[page_num].has_discontinuity = True
                self.pages[page_num].discontinuity_amount = discrepancy

            finding = {
                "category": "MATHEMATICAL_MISMATCH",
                "severity": "CRITICAL",
                "rule_id": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                "risk_points": 50,
                "title": f"Page Carried Forward Balance Mismatch on Page {page_num}",
                "description": (
                    f"Page {page_num} transactions left a calculated running balance of PKR {expected:,.2f}, "
                    f"but the Carried Forward total specifies PKR {amount:,.2f}. "
                    f"Discrepancy: PKR {discrepancy:+,.2f}."
                ),
                "expected_value": f"PKR {expected:,.2f}",
                "actual_value": f"PKR {amount:,.2f}",
                "discrepancy": f"PKR {discrepancy:+,.2f}",
                "technical_details": {
                    "running_balance": str(expected),
                    "carried_forward": str(amount),
                    "discrepancy": str(discrepancy),
                    "page_number": page_num,
                },
                "label": "Carryover Mismatch",
                "color": "#dc2626",
                "page_number": page_num,
            }
            self.discontinuities.append(finding)

        self.running_balance = amount
        if page_num in self.pages:
            self.pages[page_num].closing_balance = amount
            self.pages[page_num].closing_type = "EXPLICIT_CARRIED_FORWARD"

        self.all_ledger_rows.append({
            "date": raw_line[:11].strip() if raw_line else "—",
            "particulars": "Balance Carried Forward",
            "debit": None,
            "credit": None,
            "expectedBalance": float(expected if expected is not None else amount),
            "recordedBalance": float(amount),
            "discrepancy": float(amount - (expected or amount)),
            "isTampered": finding is not None,
            "pageNumber": page_num,
            "rowType": "CARRIED_FORWARD",
        })
        return finding

    def process_transaction(
        self,
        page_num: int,
        date_str: str,
        particulars: str,
        balance_candidate: Decimal,
        amounts: list[tuple[Decimal, Any, str]],
        raw_line: str = "",
    ) -> tuple[bool, Decimal, Optional[dict[str, Any]]]:
        """
        Reconcile a single transaction row.
        Returns: (reconciled, new_balance, finding_dict_if_any)
        """
        finding = None

        # Check if this is the very first transaction in the document without an opening row
        if not self.first_transaction_processed:
            self.first_transaction_processed = True
            debit_1 = None
            credit_1 = None
            if len(amounts) == 2:
                tx_amt = amounts[0][0]
                if tx_amt < 0:
                    debit_1 = abs(tx_amt)
                else:
                    credit_1 = abs(tx_amt)
            elif len(amounts) >= 3:
                debit_1 = abs(amounts[-3][0])
                credit_1 = abs(amounts[-2][0])

            table_origin = balance_candidate - (credit_1 or Decimal("0.00")) + (debit_1 or Decimal("0.00"))
            self.implied_opening = table_origin

            if page_num in self.pages:
                self.pages[page_num].opening_balance = table_origin
                self.pages[page_num].opening_type = "IMPLIED_ORIGIN"

            if self.stated_opening is not None and abs(table_origin - self.stated_opening) > self.tolerance:
                discrepancy = table_origin - self.stated_opening
                finding = {
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL" if abs(discrepancy) > Decimal("1000") else "HIGH",
                    "rule_id": "RULE_PK_OPENING_BALANCE_MISMATCH",
                    "risk_points": 50 if abs(discrepancy) > Decimal("1000") else 30,
                    "title": f"Opening Balance Tampering Detected (+{discrepancy:,.2f} PKR Discrepancy)" if discrepancy > 0 else f"Opening Balance Mismatch ({discrepancy:+,.2f} PKR)",
                    "description": (
                        f"Document header states Opening Balance of PKR {self.stated_opening:,.2f}, "
                        f"but back-calculated ledger origin from first transaction is PKR {table_origin:,.2f}. "
                        f"Discrepancy: PKR {discrepancy:+,.2f}. This indicates ledger origin manipulation."
                    ),
                    "expected_value": f"PKR {self.stated_opening:,.2f}",
                    "actual_value": f"PKR {table_origin:,.2f}",
                    "discrepancy": f"PKR {discrepancy:+,.2f}",
                    "technical_details": {
                        "stated_opening": str(self.stated_opening),
                        "table_origin": str(table_origin),
                        "discrepancy": str(discrepancy),
                        "page_number": page_num,
                    },
                    "label": "Ledger Origin Row",
                    "color": "#f59e0b",
                    "page_number": page_num,
                }

            self.all_ledger_rows.append({
                "date": date_str or (raw_line[:11].strip() if raw_line else "—"),
                "particulars": particulars or "Initial Transaction",
                "debit": float(debit_1) if debit_1 else None,
                "credit": float(credit_1) if credit_1 else None,
                "expectedBalance": float(balance_candidate),
                "recordedBalance": float(balance_candidate),
                "discrepancy": 0.0,
                "isTampered": False,
                "pageNumber": page_num,
                "rowType": "TRANSACTION",
            })
            self.running_balance = balance_candidate
            if page_num in self.pages:
                self.pages[page_num].tx_count += 1
                if credit_1:
                    self.pages[page_num].total_credits += credit_1
                if debit_1:
                    self.pages[page_num].total_debits += debit_1
            return True, balance_candidate, finding

        # Check for seamless carryforward across page boundary (Page N > 1 first row without explicit B/F line)
        is_page_boundary = (
            page_num > 1
            and not self.page_first_row_processed
            and self.last_page_closing_balance is not None
        )
        self.page_first_row_processed = True

        if is_page_boundary and page_num in self.pages and self.pages[page_num].opening_balance is None:
            self.pages[page_num].opening_balance = self.last_page_closing_balance
            self.pages[page_num].opening_type = "SEAMLESS_CARRYFORWARD"

        prev = self.running_balance
        if prev is None:
            # Fallback if no prior balance known
            self.running_balance = balance_candidate
            return True, balance_candidate, None

        reconciled = False
        expected_balance = None
        discrepancy = Decimal("0.00")
        rule_id = "RULE_PK_PAGE_BALANCE_DISCONTINUITY" if is_page_boundary else "RULE_PK_LEDGER_RECONCILIATION_FAIL"
        title = (
            f"Multi-Page Balance Discontinuity on Page {page_num}"
            if is_page_boundary
            else "Ledger Running Balance Mathematical Inconsistency"
        )
        boundary_note = (
            f" Across page boundary from Page {page_num - 1} (ended at PKR {self.last_page_closing_balance:,.2f}), "
            if is_page_boundary
            else ""
        )

        row_debit = None
        row_credit = None

        if len(amounts) == 2:
            tx_amount = amounts[0][0]
            abs_tx = abs(tx_amount)
            exp_credit = prev + abs_tx
            exp_debit = prev - abs_tx

            if abs(balance_candidate - exp_credit) <= self.tolerance:
                reconciled = True
                self.running_balance = balance_candidate
                row_credit = abs_tx
            elif abs(balance_candidate - exp_debit) <= self.tolerance:
                reconciled = True
                self.running_balance = balance_candidate
                row_debit = abs_tx
            else:
                expected_balance = exp_credit if balance_candidate > prev else exp_debit
                discrepancy = balance_candidate - expected_balance
                if tx_amount < 0:
                    row_debit = abs_tx
                else:
                    row_credit = abs_tx
                desc_msg = (
                    f"Transaction row on Page {page_num} ('{raw_line[:80]}...') contains an impossible "
                    f"running balance.{boundary_note} Previous balance was PKR {prev:,.2f}. Transaction amount "
                    f"is PKR {tx_amount:,.2f}. Expected resulting balance: PKR {exp_credit:,.2f} (credit) "
                    f"or PKR {exp_debit:,.2f} (debit), but statement reports PKR {balance_candidate:,.2f}. "
                    f"Discrepancy: PKR {discrepancy:+,.2f}."
                )

        elif len(amounts) >= 3:
            n1 = amounts[-3][0]
            n1_str = amounts[-3][2]
            n2 = amounts[-2][0]

            # Hyp A: Standard 3-col [Debit, Credit, Balance]
            exp_3col = prev + n2 - n1
            # Hyp B: n1 is Cheque/Ref, n2 is Credit
            exp_chq_credit = prev + abs(n2)
            # Hyp C: n1 is Cheque/Ref, n2 is Debit
            exp_chq_debit = prev - abs(n2)

            if abs(balance_candidate - exp_3col) <= self.tolerance:
                reconciled = True
                self.running_balance = balance_candidate
                row_debit = abs(n1)
                row_credit = abs(n2)
            elif ("." not in n1_str) and abs(balance_candidate - exp_chq_credit) <= self.tolerance:
                reconciled = True
                self.running_balance = balance_candidate
                row_credit = abs(n2)
            elif ("." not in n1_str) and abs(balance_candidate - exp_chq_debit) <= self.tolerance:
                reconciled = True
                self.running_balance = balance_candidate
                row_debit = abs(n2)
            else:
                row_debit = abs(n1)
                row_credit = abs(n2)
                if ("." not in n1_str) and n1 > 1000:
                    expected_balance = exp_chq_credit if balance_candidate > prev else exp_chq_debit
                    discrepancy = balance_candidate - expected_balance
                    desc_msg = (
                        f"Transaction row on Page {page_num} ('{raw_line[:80]}...') fails arithmetic reconciliation:{boundary_note} "
                        f"Previous (PKR {prev:,.2f}) ± Tx (PKR {n2:,.2f}) [Cheque No: {n1_str}] "
                        f"= Expected PKR {expected_balance:,.2f}, but statement reports PKR {balance_candidate:,.2f}. "
                        f"Discrepancy: PKR {discrepancy:+,.2f}."
                    )
                else:
                    expected_balance = exp_3col
                    discrepancy = balance_candidate - exp_3col
                    desc_msg = (
                        f"Transaction row on Page {page_num} fails arithmetic reconciliation:{boundary_note} "
                        f"Previous (PKR {prev:,.2f}) + Credit (PKR {n2:,.2f}) "
                        f"- Debit (PKR {n1:,.2f}) = Expected PKR {exp_3col:,.2f}, "
                        f"but statement reports PKR {balance_candidate:,.2f}. Discrepancy: PKR {discrepancy:+,.2f}."
                    )

        if not reconciled and expected_balance is not None:
            finding = {
                "category": "MATHEMATICAL_MISMATCH",
                "severity": "CRITICAL",
                "rule_id": rule_id,
                "risk_points": 50,
                "title": title,
                "description": desc_msg,
                "expected_value": f"PKR {expected_balance:,.2f}",
                "actual_value": f"PKR {balance_candidate:,.2f}",
                "discrepancy": f"PKR {discrepancy:+,.2f}",
                "technical_details": {
                    "line_text": raw_line,
                    "previous_balance": str(prev),
                    "reported_balance": str(balance_candidate),
                    "expected_balance": str(expected_balance),
                    "discrepancy": str(discrepancy),
                    "is_page_boundary": is_page_boundary,
                },
                "label": "Math Mismatch",
                "color": "#dc2626",
                "page_number": page_num,
            }
            if is_page_boundary:
                if page_num in self.pages:
                    self.pages[page_num].has_discontinuity = True
                    self.pages[page_num].discontinuity_amount = discrepancy
                self.discontinuities.append(finding)

        self.all_ledger_rows.append({
            "date": date_str or (raw_line[:11].strip() if raw_line else "—"),
            "particulars": particulars or (raw_line[11:65].strip() if len(raw_line) > 11 else raw_line),
            "debit": float(row_debit) if row_debit else None,
            "credit": float(row_credit) if row_credit else None,
            "expectedBalance": float(expected_balance or balance_candidate),
            "recordedBalance": float(balance_candidate),
            "discrepancy": float(discrepancy),
            "isTampered": not reconciled,
            "pageNumber": page_num,
            "rowType": "TRANSACTION",
        })

        self.running_balance = balance_candidate
        if page_num in self.pages:
            self.pages[page_num].tx_count += 1
            if row_credit:
                self.pages[page_num].total_credits += row_credit
            if row_debit:
                self.pages[page_num].total_debits += row_debit

        return reconciled, balance_candidate, finding

    def end_page(self, page_num: int) -> None:
        """
        Record the concluding balance for Page N to carry forward into Page N+1.
        """
        if page_num in self.pages:
            if self.pages[page_num].closing_balance is None:
                self.pages[page_num].closing_balance = self.running_balance
                self.pages[page_num].closing_type = "TERMINAL_TRANSACTION"

        self.last_page_closing_balance = self.running_balance

    def finalize(
        self,
        stated_closing: Optional[Decimal] = None,
        stated_credits: Optional[Decimal] = None,
        stated_debits: Optional[Decimal] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute document-level closing balance and macro summary formula audits.
        """
        final_findings = []
        cl = stated_closing if stated_closing is not None else self.stated_closing
        cr = stated_credits if stated_credits is not None else self.stated_credits
        dr = stated_debits if stated_debits is not None else self.stated_debits
        op = self.stated_opening or self.implied_opening

        # Check 1: Header Stated Closing vs Final Ledger Terminal Balance
        if cl is not None and self.running_balance is not None:
            diff_closing = abs(cl - self.running_balance)
            if diff_closing > self.tolerance:
                discrepancy = cl - self.running_balance
                title = (
                    f"Closing Balance Tampering Detected (+{discrepancy:,.2f} PKR Discrepancy)"
                    if discrepancy > 0
                    else f"Closing Balance Mismatch ({discrepancy:+,.2f} PKR)"
                )
                final_findings.append({
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL",
                    "rule_id": "RULE_PK_CLOSING_BALANCE_MISMATCH",
                    "risk_points": 50,
                    "title": title,
                    "description": (
                        f"Statement summary specifies Closing Balance of PKR {cl:,.2f}, "
                        f"but cumulative multi-page transactions yield a terminal balance of PKR {self.running_balance:,.2f}. "
                        f"Discrepancy: PKR {discrepancy:+,.2f}. This proves closing balance manipulation."
                    ),
                    "expected_value": f"PKR {self.running_balance:,.2f}",
                    "actual_value": f"PKR {cl:,.2f}",
                    "discrepancy": f"PKR {discrepancy:+,.2f}",
                    "technical_details": {
                        "stated_closing": str(cl),
                        "calculated_closing": str(self.running_balance),
                        "discrepancy": str(discrepancy),
                    },
                    "label": "Closing Balance Tampered",
                    "color": "#dc2626",
                    "page_number": max(self.pages.keys()) if self.pages else 1,
                })

        # Check 2: Macro Mathematical Identity: Opening + Credits - Debits == Closing
        if op is not None and cl is not None and cr is not None and dr is not None:
            expected_closing = op + cr - dr
            diff_macro = abs(cl - expected_closing)
            if diff_macro > self.tolerance:
                discrepancy = cl - expected_closing
                final_findings.append({
                    "category": "MATHEMATICAL_MISMATCH",
                    "severity": "CRITICAL",
                    "rule_id": "RULE_PK_STATEMENT_SUMMARY_TAMPER",
                    "risk_points": 50,
                    "title": "Statement Header Summary Arithmetic Inconsistency",
                    "description": (
                        f"Statement summary figures violate the fundamental banking identity "
                        f"(Opening Balance + Total Credits - Total Debits = Closing Balance): "
                        f"Stated Opening (PKR {op:,.2f}) + Total Credits (PKR {cr:,.2f}) "
                        f"- Total Debits (PKR {dr:,.2f}) = Expected Closing PKR {expected_closing:,.2f}, "
                        f"but statement reports Closing Balance PKR {cl:,.2f}. "
                        f"Discrepancy: PKR {discrepancy:+,.2f}. This proves forged or tampered summary figures."
                    ),
                    "expected_value": f"PKR {expected_closing:,.2f}",
                    "actual_value": f"PKR {cl:,.2f}",
                    "discrepancy": f"PKR {discrepancy:+,.2f}",
                    "technical_details": {
                        "stated_opening": str(op),
                        "stated_credits": str(cr),
                        "stated_debits": str(dr),
                        "stated_closing": str(cl),
                        "expected_closing": str(expected_closing),
                        "discrepancy": str(discrepancy),
                    },
                    "label": "Summary Arithmetic Mismatch",
                    "color": "#dc2626",
                    "page_number": 1,
                })

        return final_findings

    def get_ledger_rows(self) -> list[dict[str, Any]]:
        """Return the full multi-page ledger rows audit log."""
        return self.all_ledger_rows
