# Garments Compliance Management - Odoo 18

Advanced garments/factory compliance module for Odoo 18.

## Included

- Compliance register with expiry monitoring
- Buyer profiles and buyer-specific checklist templates
- Audit workflow, checklist lines, findings and CAPA
- Bangladesh garments starter checklist (generic starter; review before use)
- Odoo Attendance based working-hour / OT review
- Configurable hour limits and buyer/company policies
- Wage / salary / overtime-payment compliance review without requiring Enterprise Payroll
- Fire / emergency drills
- Safety equipment register with inspection/certificate due alerts
- Safety inspections, incidents / near misses, training, worker grievances
- Chemical register and environmental monitoring
- License/certificate expiry checks
- Multi-company record rules
- KPI dashboard on company cards

## Important configuration

This module intentionally does **not** hard-code Bangladesh statutory working-hour, overtime, wage, or other legal thresholds. Create a Compliance Policy under:

`Compliance > Configuration > Compliance Policies / Limits`

Enter the values that your organization has verified for the current applicable law, buyer code of conduct, certification program, collective agreement (if any), and internal policy.

The included Bangladesh starter checklist is a workflow starter, not legal advice or a claim that the checklist alone covers every legal/buyer requirement.

## Working-hour check

1. Install/use Odoo Attendance (`hr_attendance`).
2. Create a Compliance Policy with daily/weekly limits.
3. Open `Compliance > Social Compliance > Working Hours & OT`.
4. Select period, company, department/buyer and policy.
5. Click **Load Attendance**.
6. Odoo summarizes daily attendance, calculated OT, maximum weekly hours, maximum weekly OT and continuous workdays per employee.

## Wage review

The wage review is payroll-system-neutral. Add/import employee values for basic wage, gross wage, overtime hours and overtime paid. The module compares them against the selected policy and calculates expected OT from:

`basic_wage / monthly_standard_hours * overtime_multiplier * overtime_hours`

Configure that formula only if it matches your verified policy/rule.

## Installation

1. Copy folder `garment_compliance_v18` into your custom addons directory.
2. Restart Odoo.
3. Update Apps List.
4. Search **Garments Compliance Management - Advanced**.
5. Install.
6. Assign one of the Compliance security groups to users.

## Dependency

- base
- mail
- hr
- hr_attendance
- contacts

## Version

`18.0.2.0.0`


## Version 18.0.3.0.0 additions
- Vendor and subcontractor compliance with audit/certificate due reminders
- Controlled policy/SOP document register with version/supersession and review reminders
- Legal/regulatory requirement register
- Worker document verification register
- PPE issue and replacement tracking
- Safety/participation/anti-harassment/environment committee register
- Committee meetings and action tracker
- Required training matrix by department/job scope
- Compliance risk register with calculated score/level
- Daily overdue CAPA escalation activities
- Multi-company record rules and access controls for all added models

Legal, wage and work-hour thresholds remain configurable. Verify applicable current law, buyer code and factory policy before entering production values.
