"use client";

import React from "react";
import { EvidenceItem } from "@/lib/types/forensics";
import { IBANChecksumCard } from "@/components/dossier/IBANChecksumCard";
import { SBPAmlCddCard } from "@/components/dossier/SBPAmlCddCard";
import { NadraCnicCard } from "@/components/dossier/NadraCnicCard";
import { FbrTaxCard } from "@/components/dossier/FbrTaxCard";

interface RegulatoryTabProps {
  activeTab: string;
  financialData: any;
  evidence: EvidenceItem[];
}

export function RegulatoryTab({
  activeTab,
  financialData,
  evidence,
}: RegulatoryTabProps) {
  if (activeTab === "iban") {
    return (
      <div className="space-y-4">
        <IBANChecksumCard
          iban={financialData?.iban?.raw_iban}
          bankName={financialData?.iban?.bank_name}
          isValid={financialData?.iban?.is_valid}
          accountNo={financialData?.iban?.account_number}
          checkDigits={financialData?.iban?.check_digits}
          bankCode={financialData?.iban?.bank_code}
          validationReason={financialData?.iban?.validation_reason}
          evidence={evidence}
        />
        <SBPAmlCddCard
          screening={financialData?.aml_cdd_screening}
          evidence={evidence}
        />
        {financialData?.cnic_verification && (
          <NadraCnicCard
            verification={financialData?.cnic_verification}
            evidence={evidence}
          />
        )}
        {financialData?.fbr_tax_verification && (
          <FbrTaxCard
            verification={financialData?.fbr_tax_verification}
            evidence={evidence}
          />
        )}
      </div>
    );
  }

  if (activeTab === "cnic") {
    return (
      <div className="space-y-4">
        <NadraCnicCard
          verification={financialData?.cnic_verification}
          evidence={evidence}
        />
      </div>
    );
  }

  if (activeTab === "fbr") {
    return (
      <div className="space-y-4">
        <FbrTaxCard
          verification={financialData?.fbr_tax_verification}
          evidence={evidence}
        />
      </div>
    );
  }

  return null;
}
