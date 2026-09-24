# Garments Compliance Management — Odoo 18

A complete operational compliance module for garments factories. It manages master data, standards and checklists, audits, weighted scoring and grades, findings, CAPA, licenses, safety inspections, training and controlled documents.

## Audit scoring

Each completed applicable checklist line contributes to a weighted score:

- Compliant = 100% of the line weight
- Partially Compliant = 50%
- Non-Compliant = 0%
- Not Applicable = excluded
- Pending = excluded until completed and blocks audit submission

Severity multiplies the checklist weight: Low ×1, Medium ×2, High ×3, Critical ×4.

Default grade rules are configurable under **Garments Compliance → Configuration → Grade Rules**:

- A: 90.00–100.00
- B: 80.00–89.99
- C: 70.00–79.99
- D: 0.00–69.99

## Audit workflow

Draft → Scheduled → In Progress → Submitted → Reviewed → Closed

Mandatory Partial or Non-Compliant checklist lines require a Finding before submission. An audit cannot close while any Finding remains open.

## Finding and CAPA workflow

Finding: Open → Root Cause Analysis → Action In Progress → Verification → Closed

CAPA: Draft → In Progress → To Verify → Done

CAPA evidence is required before verification and verification notes are required before closure. A Finding with CAPA records cannot move to verification until all CAPA records are Done.

## Registers and automation

- License/certificate expiry calculation with Valid / Expiring Soon / Expired status
- Daily reminder activities for licenses expiring within 30 days
- Daily activities for overdue Findings
- Safety inspection workflow
- Training participant tracking
- Controlled document register
- Multi-company record rules
- Audit PDF report
- Audit pivot and graph analysis

## Starter data

The module installs a **General Garments Compliance Standard** with 16 starter checklist controls. These are examples and should be reviewed against local law, buyer requirements and certification standards before operational use.

## Installation

Copy `garments_compliance` into an Odoo 18 addons path, update the Apps list, then install **Garments Compliance Management**. Assign users to Compliance User or Compliance Manager under user access rights.


## Two operating options

### Option 1 - Buyer Audit Management
Use the Buyer Audit menu for amfori BSCI, WRAP, SEDEX/SMETA and buyer-specific audits. Starter standards and checklists are installed automatically. Findings and CAPA are shared with the full system so corrective actions remain traceable.

### Option 2 - Full Factory Compliance
Use the Full Factory Compliance menu for the dashboard, all audits, findings, CAPA, safety inspections, licenses/certificates, HR compliance, training and document control.

The supplied BSCI/WRAP/SEDEX checklists are starter operational data, not a substitute for the latest official audit protocol or certification scheme documents. Update them when a buyer or scheme changes its requirements.
