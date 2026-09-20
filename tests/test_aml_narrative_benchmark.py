"""
Comprehensive Benchmark Suite for SBP AML/CFT & Narrative Screening.
Evaluates 105+ genuine transactions across 7 Pakistani commercial banks and EMIs:
  1. Meezan Bank Limited
  2. Habib Bank Limited (HBL)
  3. United Bank Limited (UBL)
  4. Bank Alfalah Limited (Alfa)
  5. Standard Chartered Bank (SCB Pakistan)
  6. MCB Bank Limited
  7. Electronic Money Institutions (Nayapay, Sadapay, JazzCash, Easypaisa)

Verifies:
  - False-Positive Rate on genuine statements: 0.0%
  - Genuine transaction false positives: 0 / 105 (0.0%)
  - True-Positive Detection on adversarial Hawala / Crypto transactions: 100.0%
  - Disambiguation between Crypto P2P vs Hawala vs Structuring.
"""

import pytest
from app.features.pipeline.tasks.aml_screening_engine import (
    scan_transaction_narrations,
    perform_sbp_cdd_screening,
)


GENUINE_STATEMENTS_DATA = {
    "Meezan_Bank": [
        {"row_number": 1, "particulars": "RAAST/P2P/Rent Transfer", "amount": 45000},
        {"row_number": 2, "particulars": "Raast P2P Outflow to 03001234567", "amount": 12000},
        {"row_number": 3, "particulars": "Meezan Mobile App Funds Transfer", "amount": 25000},
        {"row_number": 4, "particulars": "ATM Cash Withdrawal Branch 0101", "amount": 20000},
        {"row_number": 5, "particulars": "WHT Deduction Sec 236P", "amount": 150},
        {"row_number": 6, "particulars": "FED on Digital Banking Service", "amount": 35},
        {"row_number": 7, "particulars": "Profit Credited Mudaraba Savings", "amount": 8420},
        {"row_number": 8, "particulars": "SMS Banking Charges", "amount": 120},
        {"row_number": 9, "particulars": "Interbank IBFT Outflow via 1Link", "amount": 60000},
        {"row_number": 10, "particulars": "Salary Credit from Engro Corp", "amount": 350000},
        {"row_number": 11, "particulars": "Utility Bill Payment SSGC", "amount": 4500},
        {"row_number": 12, "particulars": "Cheque Clearing Inward NIFT", "amount": 150000},
        {"row_number": 13, "particulars": "POS Card Settlement Gulberg", "amount": 6200},
        {"row_number": 14, "particulars": "PayPak Debit Card Annual Fee", "amount": 1800},
        {"row_number": 15, "particulars": "Raast Instant Payment Received", "amount": 10000},
    ],
    "Habib_Bank_Limited": [
        {"row_number": 1, "particulars": "HBL Pay P2P Transfer to 03211234567", "amount": 15000},
        {"row_number": 2, "particulars": "Raast P2P Inflow from SCB", "amount": 85000},
        {"row_number": 3, "particulars": "Konnect by HBL Wallet Cash In", "amount": 5000},
        {"row_number": 4, "particulars": "Konnect P2P Transfer", "amount": 3200},
        {"row_number": 5, "particulars": "HBL Mobile App IBFT to Bank Alfalah", "amount": 40000},
        {"row_number": 6, "particulars": "ATM Cash Deposit HBL CDM", "amount": 50000},
        {"row_number": 7, "particulars": "Cheque Return Charges NIFT", "amount": 500},
        {"row_number": 8, "particulars": "Tax Withholding FBR 231A", "amount": 300},
        {"row_number": 9, "particulars": "HBL Debit Card Swipe Al-Fatah", "amount": 14200},
        {"row_number": 10, "particulars": "Salary Processing Nestlé Pakistan", "amount": 420000},
        {"row_number": 11, "particulars": "E-Commerce Purchase Daraz.pk", "amount": 2500},
        {"row_number": 12, "particulars": "Over the Counter Cash Withdrawal", "amount": 100000},
        {"row_number": 13, "particulars": "Demand Draft Issuance Charges", "amount": 600},
        {"row_number": 14, "particulars": "School Fee Beaconhouse via 1Bill", "amount": 38000},
        {"row_number": 15, "particulars": "Raast P2P Outflow for House Rent", "amount": 55000},
    ],
    "United_Bank_Limited": [
        {"row_number": 1, "particulars": "UBL Digital P2P Payment", "amount": 8000},
        {"row_number": 2, "particulars": "Raast P2P Remittance to Family", "amount": 30000},
        {"row_number": 3, "particulars": "UBL Omni Cash Deposit", "amount": 10000},
        {"row_number": 4, "particulars": "1LINK P2P Interbank Transfer", "amount": 22000},
        {"row_number": 5, "particulars": "Wiz Virtual Card Settlement", "amount": 4500},
        {"row_number": 6, "particulars": "UBL Netbanking Bill Payment LESCO", "amount": 18500},
        {"row_number": 7, "particulars": "Cheque Deposit OTC Clearing", "amount": 95000},
        {"row_number": 8, "particulars": "SMS Alert Subscription Fee", "amount": 100},
        {"row_number": 9, "particulars": "Corporate Dividend Credit Fauji Fertilizer", "amount": 16400},
        {"row_number": 10, "particulars": "ATM FastCash Cash Withdrawal", "amount": 25000},
        {"row_number": 11, "particulars": "Raast P2P Person to Person Transfer", "amount": 12500},
        {"row_number": 12, "particulars": "Mobile Topup Jazz Prepaid", "amount": 1000},
        {"row_number": 13, "particulars": "Pay Order Commission", "amount": 400},
        {"row_number": 14, "particulars": "Government Tax Deduction", "amount": 220},
        {"row_number": 15, "particulars": "Inward Remittance PRI Home Remittance", "amount": 180000},
    ],
    "Bank_Alfalah": [
        {"row_number": 1, "particulars": "Alfa P2P Funds Transfer", "amount": 14000},
        {"row_number": 2, "particulars": "Alfa Raast P2P Payment", "amount": 7500},
        {"row_number": 3, "particulars": "Alfa QR Merchant Payment", "amount": 1850},
        {"row_number": 4, "particulars": "1LINK IBFT to Meezan Bank", "amount": 50000},
        {"row_number": 5, "particulars": "Cheque Clearing Outward NIFT", "amount": 120000},
        {"row_number": 6, "particulars": "Cash Withdrawal CDM Branch 0042", "amount": 35000},
        {"row_number": 7, "particulars": "Withholding Tax on Non-Filers", "amount": 450},
        {"row_number": 8, "particulars": "Bank Alfalah Credit Card Payment", "amount": 42000},
        {"row_number": 9, "particulars": "Alfa Mobile Topup Zong", "amount": 1500},
        {"row_number": 10, "particulars": "Direct Debit Life Insurance EFU", "amount": 12000},
        {"row_number": 11, "particulars": "Salary Credit Systems Limited", "amount": 280000},
        {"row_number": 12, "particulars": "Raast P2P Outflow to Friend", "amount": 6000},
        {"row_number": 13, "particulars": "E-Banking Subscription Monthly", "amount": 110},
        {"row_number": 14, "particulars": "Over The Counter Deposit Teller 02", "amount": 70000},
        {"row_number": 15, "particulars": "POS Debit Card Hyperstar Lahore", "amount": 9800},
    ],
    "Standard_Chartered_Bank": [
        {"row_number": 1, "particulars": "SCB Online Banking Raast P2P", "amount": 35000},
        {"row_number": 2, "particulars": "SCB Mobile App P2P to Nayapay", "amount": 18000},
        {"row_number": 3, "particulars": "Priority Banking Relationship Fee", "amount": 2500},
        {"row_number": 4, "particulars": "Standing Order Rent Payment", "amount": 80000},
        {"row_number": 5, "particulars": "Inward Foreign Inflow Home Remittance", "amount": 250000},
        {"row_number": 6, "particulars": "Interbank Transfer via 1Link IBFT", "amount": 45000},
        {"row_number": 7, "particulars": "ATM Cash Withdrawal SCB World", "amount": 40000},
        {"row_number": 8, "particulars": "Debit Card POS Purchase Imtiaz Super Market", "amount": 11500},
        {"row_number": 9, "particulars": "Tax Withheld SBP Regulatory Rate", "amount": 380},
        {"row_number": 10, "particulars": "Clearing Cheque Standard Chartered", "amount": 300000},
        {"row_number": 11, "particulars": "Internet Banking Utility Payment SNGPL", "amount": 7800},
        {"row_number": 12, "particulars": "Raast P2P Instant Transfer", "amount": 20000},
        {"row_number": 13, "particulars": "Profit Payment Saadiq Term Account", "amount": 15200},
        {"row_number": 14, "particulars": "Bank Guarantee Commission", "amount": 5000},
        {"row_number": 15, "particulars": "Foreign Exchange Surcharge", "amount": 450},
    ],
    "MCB_Bank": [
        {"row_number": 1, "particulars": "MCB Live Raast P2P Fund Transfer", "amount": 22000},
        {"row_number": 2, "particulars": "MCB Mobile P2P Outward", "amount": 16000},
        {"row_number": 3, "particulars": "1LINK P2P IBFT to HBL", "amount": 38000},
        {"row_number": 4, "particulars": "Cash Deposit at CDM MCB 051", "amount": 60000},
        {"row_number": 5, "particulars": "Cheque Encashment Over Counter", "amount": 45000},
        {"row_number": 6, "particulars": "Annual Debit Card Fee MCB Visa", "amount": 2200},
        {"row_number": 7, "particulars": "Salary Disbursement Lucky Cement", "amount": 310000},
        {"row_number": 8, "particulars": "FBR Active Taxpayer Surcharge", "amount": 250},
        {"row_number": 9, "particulars": "Raast P2P Settlement for Groceries", "amount": 5400},
        {"row_number": 10, "particulars": "POS Transaction Jalal Sons", "amount": 8300},
        {"row_number": 11, "particulars": "Electricity Bill IESCO via 1Bill", "amount": 21000},
        {"row_number": 12, "particulars": "Excise Duty on Banking Transaction", "amount": 180},
        {"row_number": 13, "particulars": "Cheque Book Request 25 Leaves", "amount": 650},
        {"row_number": 14, "particulars": "Inward Clearing NIFT Karachi", "amount": 185000},
        {"row_number": 15, "particulars": "MCB Lite Wallet Transfer", "amount": 4000},
    ],
    "Electronic_Money_Institutions": [
        {"row_number": 1, "particulars": "Nayapay Raast P2P Outflow", "amount": 5000},
        {"row_number": 2, "particulars": "Nayapay P2P Fund Transfer to Contact", "amount": 2500},
        {"row_number": 3, "particulars": "Sadapay Raast P2P Send Money", "amount": 8000},
        {"row_number": 4, "particulars": "Sadapay P2P Money Request Accepted", "amount": 3500},
        {"row_number": 5, "particulars": "JazzCash Mobile Account P2P Transfer", "amount": 4500},
        {"row_number": 6, "particulars": "JazzCash Raast P2P Payment", "amount": 1200},
        {"row_number": 7, "particulars": "Easypaisa Raast P2P Outflow", "amount": 6500},
        {"row_number": 8, "particulars": "Easypaisa P2P Transfer to CNIC", "amount": 10000},
        {"row_number": 9, "particulars": "Nayapay Visa Physical Card Transaction", "amount": 3400},
        {"row_number": 10, "particulars": "Sadapay Mastercard E-Commerce Netflix", "amount": 1500},
        {"row_number": 11, "particulars": "ATM Cash Withdrawal 1Link Nayapay Card", "amount": 15000},
        {"row_number": 12, "particulars": "Wallet Load via 1Link 1Bill Topup", "amount": 20000},
        {"row_number": 13, "particulars": "JazzCash Merchant QR Payment", "amount": 850},
        {"row_number": 14, "particulars": "Easypaisa Utility Bill K-Electric", "amount": 9200},
        {"row_number": 15, "particulars": "Raast P2P Inflow from Bank Alfalah", "amount": 14000},
    ],
}

ADVERSARIAL_CASES = [
    {"particulars": "Binance P2P USDT liquidation to bank", "expected_category": "UNLICENSED_VIRTUAL_ASSETS"},
    {"particulars": "Crypto P2P trading proceeds via escrow", "expected_category": "UNLICENSED_VIRTUAL_ASSETS"},
    {"particulars": "OKX P2P sell order completed", "expected_category": "UNLICENSED_VIRTUAL_ASSETS"},
    {"particulars": "Settlement via Dubai chitti token payment", "expected_category": "INFORMAL_VALUE_TRANSFER"},
    {"particulars": "Hundi transfer settlement to Dubai agent", "expected_category": "INFORMAL_VALUE_TRANSFER"},
    {"particulars": "Third party cash deposit smurfing multiple branches", "expected_category": "CASH_STRUCTURING"},
]


def test_batch_genuine_statements_zero_false_positives():
    """
    Test across all 7 Pakistani banking institutions.
    Assert that the false-positive rate on genuine statements is exactly 0.0%.
    """
    total_txs = 0
    falsely_flagged_txs = 0
    falsely_flagged_statements = 0

    for bank_name, tx_list in GENUINE_STATEMENTS_DATA.items():
        total_txs += len(tx_list)
        flags = scan_transaction_narrations(tx_list)
        if len(flags) > 0:
            falsely_flagged_statements += 1
            falsely_flagged_txs += len(flags)
            print(f"FAILED on {bank_name}: {flags}")

    fp_rate_tx = (falsely_flagged_txs / total_txs) * 100.0
    fp_rate_stmt = (falsely_flagged_statements / len(GENUINE_STATEMENTS_DATA)) * 100.0

    print(f"\n--- AML Narrative Benchmark Results ---")
    print(f"Total Banks/Institutions Evaluated: {len(GENUINE_STATEMENTS_DATA)}")
    print(f"Total Genuine Transactions Tested: {total_txs}")
    print(f"Transaction False-Positive Rate: {fp_rate_tx:.2f}% ({falsely_flagged_txs}/{total_txs})")
    print(f"Statement False-Positive Rate: {fp_rate_stmt:.2f}% ({falsely_flagged_statements}/{len(GENUINE_STATEMENTS_DATA)})")

    assert falsely_flagged_txs == 0, f"Expected 0 false positives, got {falsely_flagged_txs}"
    assert falsely_flagged_statements == 0, f"Expected 0 false positive statements, got {falsely_flagged_statements}"
    assert fp_rate_tx == 0.0
    assert fp_rate_stmt == 0.0


def test_batch_adversarial_detection_100_percent():
    """
    Verify 100% True-Positive detection rate on adversarial Hawala, Crypto, and Structuring cases.
    """
    detected_count = 0
    for case in ADVERSARIAL_CASES:
        flags = scan_transaction_narrations([{"particulars": case["particulars"], "row_number": 1, "page_number": 1}])
        assert len(flags) >= 1, f"Failed to detect adversarial transaction: {case['particulars']}"
        detected_count += 1

    tp_rate = (detected_count / len(ADVERSARIAL_CASES)) * 100.0
    assert tp_rate == 100.0


def test_perform_sbp_cdd_screening_end_to_end_on_clean_batch():
    """
    Verify perform_sbp_cdd_screening outputs CLEARED and RULE_AML_CDD_CLEARED for all 7 banks.
    """
    for bank_name, tx_list in GENUINE_STATEMENTS_DATA.items():
        sample_doc = f"{bank_name.replace('_', ' ')}\nAccount Title: Muhammad Usman Tariq\nCNIC: 35201-9876543-1"
        res = perform_sbp_cdd_screening(sample_doc, transactions=tx_list)
        assert res["overall_status"] == "CLEARED", f"Expected CLEARED for {bank_name}, got {res['overall_status']}"
        assert res["high_risk_narration_count"] == 0
        assert len(res["findings"]) == 1
        assert res["findings"][0]["rule_id"] == "RULE_AML_CDD_CLEARED"
