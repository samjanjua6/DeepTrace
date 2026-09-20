"""
State Bank of Pakistan (SBP) AML/CFT & Customer Due Diligence (CDD) Sanctions Dataset.
Curated, offline-first compliance registry covering:
1. National Counter Terrorism Authority (NACTA) 4th Schedule / Proscribed Entities & Persons (ATA 1997 §11EE)
2. United Nations Security Council (UNSC) 1267 / 1988 / 2253 Consolidated Sanctions List
3. Politically Exposed Persons (PEPs) Registry under SBP BPRD Circular No. 1 of 2021 & Circular No. 2 of 2012
4. Hawala, Hundi & Trade-Based Money Laundering Suspicious Narration Lexicon
"""

from typing import Any

# =============================================================================
# 1. NACTA (National Counter Terrorism Authority Pakistan) Proscribed Entities & Individuals
# Governed under Section 11B & Section 11EE of Anti-Terrorism Act 1997 (ATA 1997)
# SBP BPRD Mandate: Immediate Account Freeze, Zero Fund Transfer, Immediate STR to FMU
# =============================================================================

NACTA_PROSCRIBED_ENTITIES: list[dict[str, Any]] = [
    {
        "name": "Lashkar-e-Taiba",
        "aliases": ["LeT", "Lashkar-i-Toiba", "Lashkar-e-Tayyaba", "Pasban-e-Ahle-Hadith"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2002-01-14",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Jamat-ud-Dawa",
        "aliases": ["JuD", "Jamaat-ud-Dawah", "Falah-e-Insaniat Foundation", "FIF", "Al-Anfal Trust"],
        "category": "PROSCRIBED_ORGANIZATION",
        "notification_date": "2019-03-05",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Jaish-e-Mohammed",
        "aliases": ["JeM", "Jaish-i-Mohammed", "Tehrik-ul-Furqan", "Al-Rehman Trust", "Al-Rahmat Trust"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2002-01-14",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Tehrik-e-Taliban Pakistan",
        "aliases": ["TTP", "Tehreek-e-Taliban Pakistan", "Pakistani Taliban", "Fitna al-Khawarij"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2008-08-25",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Balochistan Liberation Army",
        "aliases": ["BLA", "Majeed Brigade", "Baloch Liberation Army"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2006-04-07",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Balochistan Liberation Front",
        "aliases": ["BLF", "Baloch Liberation Front"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2013-03-15",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Sipah-e-Sahaba Pakistan",
        "aliases": ["SSP", "Millat-e-Islamia Pakistan", "Ahle Sunnat Wal Jamaat", "ASWJ"],
        "category": "SECTARIAN_PROSCRIBED",
        "notification_date": "2002-01-14",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Lashkar-e-Jhangvi",
        "aliases": ["LeJ", "Lashkar-i-Jhangvi"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2001-08-14",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan (ATA 1997 §11B)",
    },
    {
        "name": "Daesh",
        "aliases": ["ISIL", "ISIS", "Islamic State", "ISIL-Khorasan", "ISKP", "Da'esh Khorasan"],
        "category": "GLOBAL_TERRORIST_ENTITY",
        "notification_date": "2015-08-28",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan & UNSC 2253",
    },
    {
        "name": "Al-Qaeda in the Indian Subcontinent",
        "aliases": ["AQIS", "Al-Qaida in Indian Subcontinent"],
        "category": "TERRORIST_ORGANIZATION",
        "notification_date": "2016-07-15",
        "proscription_authority": "NACTA / Ministry of Interior Pakistan & UNSC 1267",
    },
]

NACTA_PROSCRIBED_INDIVIDUALS: list[dict[str, Any]] = [
    {
        "name": "Hafiz Muhammad Saeed",
        "aliases": ["Hafiz Saeed", "Mohammad Saeed", "Hafiz Mohammad Sayeed", "Talha Saeed"],
        "cnic": "35201-1428591-1",
        "father_name": "Kamal-ud-Din",
        "role": "Chief / Founder of JuD / LeT",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.263",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Maulana Masood Azhar",
        "aliases": ["Masood Azhar", "Mohammad Masood Azhar Alvi", "Mufti Masood Azhar"],
        "cnic": "31202-0382914-7",
        "father_name": "Allah Bakhsh Sabir",
        "role": "Founder / Amir of Jaish-e-Mohammed",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.422",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Zaki-ur-Rehman Lakhvi",
        "aliases": ["Zaki ur Rehman", "Zakiur Rehman Lakhvi", "Kaki Ur-Rehman"],
        "cnic": "38403-2948172-3",
        "father_name": "Hafiz Aziz-ur-Rehman",
        "role": "Operations Commander of LeT",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.264",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Dawood Ibrahim",
        "aliases": ["Dawood Ibrahim Kaskar", "Sheikh Dawood Hassan", "Bada Rajan"],
        "cnic": None,
        "father_name": "Ibrahim Kaskar",
        "role": "Head of D-Company / Organised Transnational Crime",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.135",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Noor Wali Mehsud",
        "aliases": ["Abu Mansoor Asim", "Noor Wali", "Mufti Noor Wali Mehsud"],
        "cnic": None,
        "father_name": "Haji Gul Shah Khan",
        "role": "Leader of Tehrik-e-Taliban Pakistan (TTP)",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.427",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Abdul Rehman Makki",
        "aliases": ["Hafiz Abdul Rehman Makki", "Abdul Rahman Makki"],
        "cnic": "35201-8392104-5",
        "father_name": "Hafiz Abdullah",
        "role": "Deputy Amir of Jamat-ud-Dawa",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE) & UNSC QDi.436",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Sajid Mir",
        "aliases": ["Sajid Majid", "Ibrahim Sajid", "Uncle Bill"],
        "cnic": "35202-9182371-9",
        "father_name": "Abdul Majid Mir",
        "role": "External Operations Commander of LeT",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE)",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Mufti Abdul Rauf Asghar",
        "aliases": ["Abdul Rauf", "Mufti Rauf Asghar Alvi", "Rauf Asghar"],
        "cnic": "31202-4918204-1",
        "father_name": "Allah Bakhsh Sabir",
        "role": "Senior Commander of Jaish-e-Mohammed",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE)",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Gulzar Imam",
        "aliases": ["Shambay", "Gulzar Imam Shambay"],
        "cnic": "54401-1928374-5",
        "father_name": "Imam Bakhsh",
        "role": "Founder / Head of Baloch Nationalist Army (BNA)",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE)",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Dr. Allah Nazar Baloch",
        "aliases": ["Allah Nazar", "Dr. Allah Nazar"],
        "cnic": "52201-9283741-3",
        "father_name": "Nabi Bakhsh",
        "role": "Chief Commander of Balochistan Liberation Front (BLF)",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE)",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
    {
        "name": "Bashir Zeb Baloch",
        "aliases": ["Bashir Zeb", "Commander Bashir"],
        "cnic": None,
        "father_name": "Zeb Khan",
        "role": "Commander of Balochistan Liberation Army (BLA)",
        "statutory_reference": "NACTA 4th Schedule (ATA 1997 §11EE)",
        "action_directive": "MANDATORY_STR_AND_ACCOUNT_FREEZE",
    },
]

# =============================================================================
# 2. United Nations Security Council (UNSC) Consolidated Sanctions List
# Governed under United Nations (Security Council) Act 1948 & SBP Regulations
# SBP BPRD Mandate: Immediate Asset Freeze without Prior Notice
# =============================================================================

UNSC_SANCTIONED_INDIVIDUALS: list[dict[str, Any]] = [
    {
        "name": "Hafiz Muhammad Saeed",
        "unsc_id": "QDi.263",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2008-12-10",
        "nationality": "Pakistan",
        "statutory_reference": "UNSC Resolution 1267 & SBP BPRD Circular 1/2021",
    },
    {
        "name": "Mohammed Masood Azhar Alvi",
        "unsc_id": "QDi.422",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2019-05-01",
        "nationality": "Pakistan",
        "statutory_reference": "UNSC Resolution 1267 & SBP BPRD Circular 1/2021",
    },
    {
        "name": "Zaki-ur-Rehman Lakhvi",
        "unsc_id": "QDi.264",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2008-12-10",
        "nationality": "Pakistan",
        "statutory_reference": "UNSC Resolution 1267 & SBP BPRD Circular 1/2021",
    },
    {
        "name": "Haji Muhammad Ashraf",
        "unsc_id": "QDi.265",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2008-12-10",
        "nationality": "Pakistan",
        "statutory_reference": "UNSC Resolution 1267 & SBP BPRD Circular 1/2021",
    },
    {
        "name": "Mahmoud Mohammad Ahmed Bahaziq",
        "unsc_id": "QDi.266",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2008-12-10",
        "nationality": "Saudi Arabia / Pakistan",
        "statutory_reference": "UNSC Resolution 1267 & SBP BPRD Circular 1/2021",
    },
    {
        "name": "Ayman al-Zawahiri",
        "unsc_id": "QDi.003",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2001-10-06",
        "nationality": "Egypt",
        "statutory_reference": "UNSC Resolution 1267",
    },
    {
        "name": "Sirajuddin Jallaloudine Haqqani",
        "unsc_id": "TAi.144",
        "committee": "1988 Sanctions Committee (Taliban)",
        "designation_date": "2007-09-13",
        "nationality": "Afghanistan",
        "statutory_reference": "UNSC Resolution 1988",
    },
    {
        "name": "Mullah Mohammad Hassan Akhund",
        "unsc_id": "TAi.002",
        "committee": "1988 Sanctions Committee (Taliban)",
        "designation_date": "2001-01-25",
        "nationality": "Afghanistan",
        "statutory_reference": "UNSC Resolution 1988",
    },
    {
        "name": "Amir Muhammad Sa'id Abdal-Rahman al-Mawla",
        "unsc_id": "QDi.426",
        "committee": "1267 / 1989 / 2253 ISIL (Da'esh) & Al-Qaida Sanctions Committee",
        "designation_date": "2020-05-21",
        "nationality": "Iraq",
        "statutory_reference": "UNSC Resolution 1267",
    },
]

# =============================================================================
# 3. Politically Exposed Persons (PEPs) Registry
# SBP BPRD Circular No. 1 of 2021 (Regulation-2 & Guidelines on PEPs)
# Mandatory Requirements: Senior Management Approval (SMA), Enhanced Due Diligence (EDD),
# Determination of Source of Wealth & Source of Funds.
# =============================================================================

PEP_REGISTRY: list[dict[str, Any]] = [
    # --- Heads of State & Government ---
    {
        "name": "Mian Muhammad Shehbaz Sharif",
        "aliases": ["Shehbaz Sharif", "Mian Shehbaz Sharif", "Shahbaz Sharif"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Prime Minister of the Islamic Republic of Pakistan",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Government (SBP BPRD Guidelines on PEPs)",
    },
    {
        "name": "Mian Muhammad Nawaz Sharif",
        "aliases": ["Nawaz Sharif", "Mian Nawaz Sharif"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Former Prime Minister / Party Leader",
        "risk_level": "HIGH",
        "statutory_ground": "Former Head of Government / Close Associate",
    },
    {
        "name": "Asif Ali Zardari",
        "aliases": ["Asif Zardari", "Asif A. Zardari"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "President of the Islamic Republic of Pakistan",
        "risk_level": "HIGH",
        "statutory_ground": "Head of State (SBP BPRD Guidelines on PEPs)",
    },
    {
        "name": "Bilawal Bhutto Zardari",
        "aliases": ["Bilawal Bhutto", "Bilawal Zardari", "Bilawal B. Zardari"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Former Foreign Minister / Chairman PPP / Member of National Assembly",
        "risk_level": "HIGH",
        "statutory_ground": "Former Senior Cabinet Minister / Parliamentarian",
    },
    {
        "name": "Imran Ahmad Khan Niazi",
        "aliases": ["Imran Khan", "Imran Khan Niazi"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Former Prime Minister of Pakistan / Party Leader",
        "risk_level": "HIGH",
        "statutory_ground": "Former Head of Government (SBP BPRD Guidelines on PEPs)",
    },
    # --- Federal Ministers & Senior Cabinet ---
    {
        "name": "Mohammad Ishaq Dar",
        "aliases": ["Ishaq Dar", "Mohammad Ishaq Dar", "Senator Ishaq Dar"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Deputy Prime Minister / Foreign Minister / Former Finance Minister",
        "risk_level": "HIGH",
        "statutory_ground": "Senior Federal Cabinet Minister",
    },
    {
        "name": "Khawaja Muhammad Asif",
        "aliases": ["Khawaja Asif", "Khawaja M. Asif"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Federal Minister for Defence",
        "risk_level": "HIGH",
        "statutory_ground": "Senior Federal Cabinet Minister",
    },
    {
        "name": "Mohsin Raza Naqvi",
        "aliases": ["Mohsin Naqvi", "Syed Mohsin Raza Naqvi"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Federal Minister for Interior / Chairman PCB / Former Caretaker CM Punjab",
        "risk_level": "HIGH",
        "statutory_ground": "Federal Minister & Caretaker Chief Minister",
    },
    {
        "name": "Rana Sanaullah Khan",
        "aliases": ["Rana Sanaullah", "Rana Sana Ullah"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Advisor to PM on Political Affairs / Former Federal Interior Minister",
        "risk_level": "HIGH",
        "statutory_ground": "Senior Cabinet Minister / Advisor to PM",
    },
    {
        "name": "Maryam Nawaz Sharif",
        "aliases": ["Maryam Nawaz", "Maryam Safdar"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Chief Minister of the Province of Punjab",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Provincial Government (Provincial Chief Minister)",
    },
    {
        "name": "Syed Murad Ali Shah",
        "aliases": ["Murad Ali Shah", "Syed Murad Ali Shah"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Chief Minister of the Province of Sindh",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Provincial Government (Provincial Chief Minister)",
    },
    {
        "name": "Ali Amin Khan Gandapur",
        "aliases": ["Ali Amin Gandapur", "Ali Amin Khan"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Chief Minister of Khyber Pakhtunkhwa",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Provincial Government (Provincial Chief Minister)",
    },
    {
        "name": "Mir Sarfraz Bugti",
        "aliases": ["Sarfraz Bugti", "Mir Sarfaraz Bugti"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Chief Minister of Balochistan / Former Federal Interior Minister",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Provincial Government (Provincial Chief Minister)",
    },
    # --- Financial Regulators & Sovereign Institutions ---
    {
        "name": "Jameel Ahmad",
        "aliases": ["Jameel Ahmed", "Governor SBP"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Governor, State Bank of Pakistan (Central Bank)",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Financial Regulatory Authority (SBP)",
    },
    {
        "name": "Muhammad Aurangzeb",
        "aliases": ["Muhammad Aurangzeb Khan", "Finance Minister Aurangzeb"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Federal Minister for Finance & Revenue / Former HBL CEO",
        "risk_level": "HIGH",
        "statutory_ground": "Federal Minister of Finance & Economic Affairs",
    },
    {
        "name": "Akif Saeed",
        "aliases": ["Chairman SECP", "Akif Saeed SECP"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Chairman, Securities and Exchange Commission of Pakistan (SECP)",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Capital Markets Regulatory Authority",
    },
    {
        "name": "Malik Amjed Zubair Tiwana",
        "aliases": ["Amjad Zubair Tiwana", "Chairman FBR"],
        "pep_type": "DOMESTIC_PEP",
        "public_office": "Former Chairman, Federal Board of Revenue (FBR)",
        "risk_level": "HIGH",
        "statutory_ground": "Head of Revenue Authority",
    },
]

# =============================================================================
# 4. Hawala, Hundi, Cash Structuring & Smurfing Lexicon
# SBP BPRD AML/CFT Red Flags for Narrative Counterparty Scanning
# =============================================================================

AML_HIGH_RISK_NARRATION_KEYWORDS: list[dict[str, str]] = [
    {
        "term": "hawala",
        "category": "INFORMAL_VALUE_TRANSFER",
        "description": "Informal Hawala payment channel reference.",
    },
    {
        "term": "hundi",
        "category": "INFORMAL_VALUE_TRANSFER",
        "description": "Informal Hundi value remittance reference.",
    },
    {
        "term": "chitti",
        "category": "INFORMAL_VALUE_TRANSFER",
        "description": "Hawala token/chitti settlement indicator.",
    },
    {
        "term": "token payment",
        "category": "UNOFFICIAL_SETTLEMENT",
        "description": "Unofficial Hawala/Hundi token settlement.",
    },
    {
        "term": "crypto",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Cryptocurrency transaction prohibited under SBP BPRD Circular No. 3 of 2018.",
    },
    {
        "term": "usdt",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Tether USDT crypto asset settlement via offshore exchange.",
    },
    {
        "term": "binance",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Binance cryptocurrency exchange trade or liquidation.",
    },
    {
        "term": "binance p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Binance peer-to-peer crypto liquidation prohibited under SBP BPRD Circular No. 3 of 2018.",
    },
    {
        "term": "crypto p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Peer-to-peer cryptocurrency trading prohibited under SBP regulations.",
    },
    {
        "term": "p2p usdt",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "USDT Tether peer-to-peer trading or liquidation.",
    },
    {
        "term": "usdt p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "USDT Tether peer-to-peer trading or liquidation.",
    },
    {
        "term": "okx p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "OKX crypto peer-to-peer exchange trade.",
    },
    {
        "term": "bybit p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Bybit crypto peer-to-peer exchange trade.",
    },
    {
        "term": "kucoin p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "KuCoin crypto peer-to-peer exchange trade.",
    },
    {
        "term": "paxful p2p",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Paxful peer-to-peer crypto remittance/trade.",
    },
    {
        "term": "p2p trade",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Unlicensed peer-to-peer digital asset trade.",
    },
    {
        "term": "p2p trading",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Unlicensed peer-to-peer digital asset trading.",
    },
    {
        "term": "p2p escrow",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Peer-to-peer crypto escrow settlement indicator.",
    },
    {
        "term": "p2p liquidation",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Peer-to-peer crypto asset liquidation into fiat.",
    },
    {
        "term": "bitcoin",
        "category": "UNLICENSED_VIRTUAL_ASSETS",
        "description": "Bitcoin asset transaction.",
    },
    {
        "term": "smurfing",
        "category": "STRUCTURING",
        "description": "Explicit structuring or smurfing indicator.",
    },
    {
        "term": "benami",
        "category": "BENAMI_TRANSACTION",
        "description": "Benami account indicator prohibited under Benami Transactions (Prohibition) Act 2017.",
    },
    {
        "term": "third party cash deposit",
        "category": "CASH_STRUCTURING",
        "description": "High-risk third party cash structuring indicator.",
    },
]
