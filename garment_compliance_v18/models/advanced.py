from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentCompliancePolicy(models.Model):
    _name = 'garment.compliance.policy'
    _description = 'Garments Compliance Policy / Threshold'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'buyer_id, name'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    buyer_id = fields.Many2one('garment.compliance.buyer', tracking=True)
    active = fields.Boolean(default=True)
    notes = fields.Html(help='Document the source of these thresholds, e.g. company policy, buyer code, or applicable law.')

    standard_daily_hours = fields.Float(string='Standard Daily Hours', help='Used only to split regular and overtime hours. Configure before automated checks.')
    max_daily_ot_hours = fields.Float(string='Maximum Daily OT Hours')
    max_weekly_hours = fields.Float(string='Maximum Weekly Total Hours')
    max_weekly_ot_hours = fields.Float(string='Maximum Weekly OT Hours')
    max_continuous_workdays = fields.Integer(string='Maximum Continuous Workdays')
    workhour_tolerance = fields.Float(string='Hour Tolerance', default=0.01)

    minimum_gross_wage = fields.Monetary(string='Minimum Gross Wage / Policy Floor', currency_field='currency_id')
    monthly_standard_hours = fields.Float(string='Monthly Standard Hours', help='Used to calculate an expected overtime amount from basic wage.')
    overtime_multiplier = fields.Float(string='OT Rate Multiplier')
    wage_tolerance = fields.Monetary(string='Wage Tolerance', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)


class GarmentChecklistTemplate(models.Model):
    _name = 'garment.compliance.checklist.template'
    _description = 'Buyer / Compliance Checklist Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'buyer_id, name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char()
    company_id = fields.Many2one('res.company', index=True, help='Leave empty to make this template available to all companies.')
    buyer_id = fields.Many2one('garment.compliance.buyer', tracking=True)
    country_code = fields.Char(default='BD', string='Country Code')
    audit_type = fields.Selection([
        ('buyer', 'Buyer Audit'), ('internal', 'Internal Audit'), ('social', 'Social Audit'),
        ('safety', 'Safety Audit'), ('environment', 'Environmental Audit'),
        ('security', 'Security Audit'), ('quality', 'Quality Audit')
    ], default='buyer', required=True)
    active = fields.Boolean(default=True)
    notes = fields.Html()
    line_ids = fields.One2many('garment.compliance.checklist.template.line', 'template_id', string='Checklist')

    def action_create_audit(self):
        self.ensure_one()
        audit = self.env['garment.compliance.audit'].create({
            'name': _('%s Audit') % self.name,
            'audit_type': self.audit_type,
            'buyer_id': self.buyer_id.id,
            'company_id': self.company_id.id or self.env.company.id,
            'template_id': self.id,
        })
        audit.action_load_template()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Audit'),
            'res_model': 'garment.compliance.audit',
            'view_mode': 'form',
            'res_id': audit.id,
            'target': 'current',
        }


class GarmentChecklistTemplateLine(models.Model):
    _name = 'garment.compliance.checklist.template.line'
    _description = 'Checklist Template Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one('garment.compliance.checklist.template', required=True, ondelete='cascade')
    section = fields.Char(required=True)
    question = fields.Char(required=True)
    severity = fields.Selection([('minor', 'Minor'), ('major', 'Major'), ('critical', 'Critical')], default='minor')
    evidence_required = fields.Boolean()
    guidance = fields.Text()


class GarmentComplianceAuditExtend(models.Model):
    _inherit = 'garment.compliance.audit'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)
    template_id = fields.Many2one('garment.compliance.checklist.template', string='Checklist Template')

    def action_load_template(self):
        for audit in self:
            if not audit.template_id:
                raise UserError(_('Select a checklist template first.'))
            commands = [(5, 0, 0)]
            for line in audit.template_id.line_ids:
                commands.append((0, 0, {
                    'sequence': line.sequence,
                    'section': line.section,
                    'question': line.question,
                    'severity': line.severity,
                    'evidence_required': line.evidence_required,
                    'template_line_id': line.id,
                }))
            audit.line_ids = commands
            if audit.template_id.buyer_id and not audit.buyer_id:
                audit.buyer_id = audit.template_id.buyer_id


class GarmentComplianceAuditLineExtend(models.Model):
    _inherit = 'garment.compliance.audit.line'

    template_line_id = fields.Many2one('garment.compliance.checklist.template.line', readonly=True)
    severity = fields.Selection([('minor', 'Minor'), ('major', 'Major'), ('critical', 'Critical')], default='minor')
    evidence_required = fields.Boolean()


class GarmentComplianceBuyerExtend(models.Model):
    _inherit = 'garment.compliance.buyer'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)
    policy_id = fields.Many2one('garment.compliance.policy', string='Default Compliance Policy')
    checklist_template_ids = fields.One2many('garment.compliance.checklist.template', 'buyer_id')


class GarmentComplianceFindingExtend(models.Model):
    _inherit = 'garment.compliance.finding'

    company_id = fields.Many2one('res.company', related='audit_id.company_id', store=True, index=True)


class GarmentComplianceCapaExtend(models.Model):
    _inherit = 'garment.compliance.capa'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        finding_model = self.env['garment.compliance.finding']
        for vals in vals_list:
            if vals.get('finding_id') and not vals.get('company_id'):
                vals['company_id'] = finding_model.browse(vals['finding_id']).company_id.id
        return super().create(vals_list)

    @api.onchange('finding_id')
    def _onchange_finding_company(self):
        if self.finding_id and self.finding_id.company_id:
            self.company_id = self.finding_id.company_id


class GarmentSafetyCompanyExtend(models.Model):
    _inherit = 'garment.compliance.safety'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentTrainingCompanyExtend(models.Model):
    _inherit = 'garment.compliance.training'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentGrievanceCompanyExtend(models.Model):
    _inherit = 'garment.compliance.grievance'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentIncidentCompanyExtend(models.Model):
    _inherit = 'garment.compliance.incident'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentChemicalCompanyExtend(models.Model):
    _inherit = 'garment.compliance.chemical'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentEnvironmentCompanyExtend(models.Model):
    _inherit = 'garment.compliance.environment'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)


class GarmentWorkhourReview(models.Model):
    _name = 'garment.compliance.workhour.review'
    _description = 'Working Hour and Overtime Compliance Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    buyer_id = fields.Many2one('garment.compliance.buyer', tracking=True)
    department_id = fields.Many2one('hr.department')
    policy_id = fields.Many2one('garment.compliance.policy', required=True, tracking=True)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.context_today(self), 'month'))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('garment.compliance.workhour.review.line', 'review_id', string='Employees')
    employee_count = fields.Integer(compute='_compute_kpis', store=True)
    non_compliant_count = fields.Integer(compute='_compute_kpis', store=True)
    compliance_rate = fields.Float(compute='_compute_kpis', store=True, digits=(16, 2))
    state = fields.Selection([('draft', 'Draft'), ('reviewed', 'Reviewed'), ('closed', 'Closed')], default='draft', tracking=True)
    notes = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('garment.compliance.workhour.review') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.status')
    def _compute_kpis(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.non_compliant_count = len(rec.line_ids.filtered(lambda l: l.status == 'non_compliant'))
            checked = rec.line_ids.filtered(lambda l: l.status in ('compliant', 'non_compliant'))
            compliant = len(checked.filtered(lambda l: l.status == 'compliant'))
            rec.compliance_rate = (100.0 * compliant / len(checked)) if checked else 0.0

    @api.onchange('buyer_id')
    def _onchange_buyer_policy(self):
        if self.buyer_id and self.buyer_id.policy_id:
            self.policy_id = self.buyer_id.policy_id

    def action_load_attendance(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Start date cannot be after end date.'))
        if not self.policy_id:
            raise UserError(_('Select a compliance policy before loading attendance.'))

        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        start_local = user_tz.localize(datetime.combine(self.date_from, time.min))
        end_local = user_tz.localize(datetime.combine(self.date_to + timedelta(days=1), time.min))
        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        domain = [
            ('check_in', '>=', fields.Datetime.to_string(start_utc)),
            ('check_in', '<', fields.Datetime.to_string(end_utc)),
            ('employee_id.company_id', '=', self.company_id.id),
        ]
        if self.department_id:
            domain.append(('employee_id.department_id', '=', self.department_id.id))

        attendances = self.env['hr.attendance'].search(domain, order='employee_id, check_in')
        by_employee = defaultdict(list)
        for attendance in attendances:
            by_employee[attendance.employee_id.id].append(attendance)

        commands = [(5, 0, 0)]
        std_daily = self.policy_id.standard_daily_hours
        for employee_id, rows in by_employee.items():
            employee = self.env['hr.employee'].browse(employee_id)
            daily = defaultdict(float)
            for attendance in rows:
                local_dt = fields.Datetime.context_timestamp(self, attendance.check_in)
                daily[local_dt.date()] += attendance.worked_hours or 0.0

            regular_hours = 0.0
            overtime_hours = 0.0
            max_daily_ot = 0.0
            weekly_total = defaultdict(float)
            weekly_ot = defaultdict(float)
            for work_date, worked in daily.items():
                if std_daily > 0:
                    regular = min(worked, std_daily)
                    overtime = max(0.0, worked - std_daily)
                else:
                    regular = worked
                    overtime = 0.0
                regular_hours += regular
                overtime_hours += overtime
                max_daily_ot = max(max_daily_ot, overtime)
                week_key = work_date.isocalendar()[:2]
                weekly_total[week_key] += worked
                weekly_ot[week_key] += overtime

            dates = sorted(daily)
            max_continuous = 0
            current = 0
            previous = None
            for work_date in dates:
                if previous and work_date == previous + timedelta(days=1):
                    current += 1
                else:
                    current = 1
                max_continuous = max(max_continuous, current)
                previous = work_date

            commands.append((0, 0, {
                'employee_id': employee.id,
                'regular_hours': regular_hours,
                'overtime_hours': overtime_hours,
                'max_daily_ot_hours_observed': max_daily_ot,
                'max_weekly_hours_observed': max(weekly_total.values()) if weekly_total else 0.0,
                'max_weekly_ot_hours_observed': max(weekly_ot.values()) if weekly_ot else 0.0,
                'max_continuous_days': max_continuous,
                'attendance_days': len(dates),
            }))
        self.line_ids = commands
        return True

    def action_review(self):
        self.write({'state': 'reviewed'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class GarmentWorkhourReviewLine(models.Model):
    _name = 'garment.compliance.workhour.review.line'
    _description = 'Working Hour Review Line'
    _order = 'employee_id'

    review_id = fields.Many2one('garment.compliance.workhour.review', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    attendance_days = fields.Integer()
    regular_hours = fields.Float()
    overtime_hours = fields.Float()
    total_hours = fields.Float(compute='_compute_status', store=True)
    max_daily_ot_hours_observed = fields.Float(string='Max Daily OT')
    max_weekly_hours_observed = fields.Float(string='Max Weekly Hours')
    max_weekly_ot_hours_observed = fields.Float(string='Max Weekly OT')
    max_continuous_days = fields.Integer()
    issue_reason = fields.Text(compute='_compute_status', store=True)
    status = fields.Selection([
        ('compliant', 'Compliant'), ('non_compliant', 'Non-Compliant'), ('no_rule', 'No Rule Configured')
    ], compute='_compute_status', store=True)

    _sql_constraints = [
        ('review_employee_unique', 'unique(review_id, employee_id)', 'Each employee can appear only once in a working-hour review.'),
    ]

    @api.depends(
        'regular_hours', 'overtime_hours', 'max_daily_ot_hours_observed', 'max_weekly_hours_observed',
        'max_weekly_ot_hours_observed', 'max_continuous_days',
        'review_id.policy_id.max_daily_ot_hours', 'review_id.policy_id.max_weekly_hours',
        'review_id.policy_id.max_weekly_ot_hours', 'review_id.policy_id.max_continuous_workdays',
        'review_id.policy_id.workhour_tolerance'
    )
    def _compute_status(self):
        for line in self:
            line.total_hours = line.regular_hours + line.overtime_hours
            policy = line.review_id.policy_id
            if not policy:
                line.status = 'no_rule'
                line.issue_reason = _('No policy selected.')
                continue
            configured = any([
                policy.max_daily_ot_hours > 0, policy.max_weekly_hours > 0,
                policy.max_weekly_ot_hours > 0, policy.max_continuous_workdays > 0,
            ])
            if not configured:
                line.status = 'no_rule'
                line.issue_reason = _('No working-hour limits are configured in the selected policy.')
                continue
            tol = policy.workhour_tolerance or 0.0
            issues = []
            if policy.max_daily_ot_hours > 0 and line.max_daily_ot_hours_observed > policy.max_daily_ot_hours + tol:
                issues.append(_('Daily OT %.2f exceeds limit %.2f') % (line.max_daily_ot_hours_observed, policy.max_daily_ot_hours))
            if policy.max_weekly_hours > 0 and line.max_weekly_hours_observed > policy.max_weekly_hours + tol:
                issues.append(_('Weekly hours %.2f exceed limit %.2f') % (line.max_weekly_hours_observed, policy.max_weekly_hours))
            if policy.max_weekly_ot_hours > 0 and line.max_weekly_ot_hours_observed > policy.max_weekly_ot_hours + tol:
                issues.append(_('Weekly OT %.2f exceeds limit %.2f') % (line.max_weekly_ot_hours_observed, policy.max_weekly_ot_hours))
            if policy.max_continuous_workdays > 0 and line.max_continuous_days > policy.max_continuous_workdays:
                issues.append(_('Continuous workdays %s exceed limit %s') % (line.max_continuous_days, policy.max_continuous_workdays))
            line.status = 'non_compliant' if issues else 'compliant'
            line.issue_reason = '\n'.join(issues)


class GarmentWageReview(models.Model):
    _name = 'garment.compliance.wage.review'
    _description = 'Wage and Overtime Payment Compliance Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_start desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    buyer_id = fields.Many2one('garment.compliance.buyer', tracking=True)
    department_id = fields.Many2one('hr.department')
    policy_id = fields.Many2one('garment.compliance.policy', required=True, tracking=True)
    period_start = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.context_today(self), 'month'))
    period_end = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('garment.compliance.wage.review.line', 'review_id')
    employee_count = fields.Integer(compute='_compute_kpis', store=True)
    non_compliant_count = fields.Integer(compute='_compute_kpis', store=True)
    compliance_rate = fields.Float(compute='_compute_kpis', store=True, digits=(16, 2))
    state = fields.Selection([('draft', 'Draft'), ('reviewed', 'Reviewed'), ('closed', 'Closed')], default='draft', tracking=True)
    notes = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('garment.compliance.wage.review') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.status')
    def _compute_kpis(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.non_compliant_count = len(rec.line_ids.filtered(lambda l: l.status == 'non_compliant'))
            checked = rec.line_ids.filtered(lambda l: l.status in ('compliant', 'non_compliant'))
            compliant = len(checked.filtered(lambda l: l.status == 'compliant'))
            rec.compliance_rate = (100.0 * compliant / len(checked)) if checked else 0.0

    @api.onchange('buyer_id')
    def _onchange_buyer_policy(self):
        if self.buyer_id and self.buyer_id.policy_id:
            self.policy_id = self.buyer_id.policy_id

    def action_load_employees(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('active', '=', True)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        employees = self.env['hr.employee'].search(domain, order='name')
        self.line_ids = [(5, 0, 0)] + [(0, 0, {'employee_id': employee.id}) for employee in employees]
        return True

    def action_review(self):
        if any(rec.period_start > rec.period_end for rec in self):
            raise UserError(_('Period start cannot be after period end.'))
        self.write({'state': 'reviewed'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class GarmentWageReviewLine(models.Model):
    _name = 'garment.compliance.wage.review.line'
    _description = 'Wage Compliance Review Line'
    _order = 'employee_id'

    review_id = fields.Many2one('garment.compliance.wage.review', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    currency_id = fields.Many2one('res.currency', related='review_id.company_id.currency_id', readonly=True)
    basic_wage = fields.Monetary(currency_field='currency_id')
    gross_wage = fields.Monetary(currency_field='currency_id')
    overtime_hours = fields.Float()
    overtime_paid = fields.Monetary(currency_field='currency_id')
    expected_overtime_pay = fields.Monetary(compute='_compute_status', store=True, currency_field='currency_id')
    wage_gap = fields.Monetary(compute='_compute_status', store=True, currency_field='currency_id')
    overtime_gap = fields.Monetary(compute='_compute_status', store=True, currency_field='currency_id')
    status = fields.Selection([
        ('compliant', 'Compliant'), ('non_compliant', 'Non-Compliant'), ('no_rule', 'No Rule Configured')
    ], compute='_compute_status', store=True)
    issue_reason = fields.Text(compute='_compute_status', store=True)
    notes = fields.Char()

    _sql_constraints = [
        ('wage_review_employee_unique', 'unique(review_id, employee_id)', 'Each employee can appear only once in a wage review.'),
    ]

    @api.depends(
        'basic_wage', 'gross_wage', 'overtime_hours', 'overtime_paid',
        'review_id.policy_id.minimum_gross_wage', 'review_id.policy_id.monthly_standard_hours',
        'review_id.policy_id.overtime_multiplier', 'review_id.policy_id.wage_tolerance'
    )
    def _compute_status(self):
        for line in self:
            policy = line.review_id.policy_id
            expected_ot = 0.0
            if policy and policy.monthly_standard_hours > 0 and policy.overtime_multiplier > 0:
                expected_ot = (line.basic_wage / policy.monthly_standard_hours) * policy.overtime_multiplier * line.overtime_hours
            line.expected_overtime_pay = expected_ot
            line.wage_gap = (line.gross_wage - policy.minimum_gross_wage) if policy else 0.0
            line.overtime_gap = line.overtime_paid - expected_ot

            if not policy:
                line.status = 'no_rule'
                line.issue_reason = _('No policy selected.')
                continue
            wage_rule = policy.minimum_gross_wage > 0
            ot_rule = policy.monthly_standard_hours > 0 and policy.overtime_multiplier > 0
            if not wage_rule and not ot_rule:
                line.status = 'no_rule'
                line.issue_reason = _('No wage or overtime payment rules are configured in the selected policy.')
                continue

            tol = policy.wage_tolerance or 0.0
            issues = []
            if wage_rule and line.gross_wage + tol < policy.minimum_gross_wage:
                issues.append(_('Gross wage is below configured policy floor by %.2f') % abs(line.wage_gap))
            if ot_rule and line.overtime_paid + tol < expected_ot:
                issues.append(_('Overtime payment is below calculated amount by %.2f') % abs(line.overtime_gap))
            line.status = 'non_compliant' if issues else 'compliant'
            line.issue_reason = '\n'.join(issues)


class GarmentComplianceFireDrill(models.Model):
    _name = 'garment.compliance.fire.drill'
    _description = 'Fire and Emergency Drill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'drill_date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    drill_date = fields.Datetime(required=True, default=fields.Datetime.now, tracking=True)
    drill_type = fields.Selection([('fire', 'Fire Drill'), ('evacuation', 'Evacuation Drill'), ('earthquake', 'Earthquake Drill'), ('other', 'Other')], default='fire', required=True)
    shift = fields.Char()
    department_id = fields.Many2one('hr.department')
    planned_headcount = fields.Integer(string='Planned / On-site Headcount')
    participant_count = fields.Integer()
    evacuation_minutes = fields.Float(string='Evacuation Time (Minutes)')
    alarm_worked = fields.Boolean()
    muster_complete = fields.Boolean(string='Muster / Headcount Complete')
    emergency_team_present = fields.Boolean()
    observer_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    responsible_id = fields.Many2one('res.users')
    next_drill_date = fields.Date()
    issues = fields.Text()
    corrective_action = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment', string='Photos / Evidence')
    state = fields.Selection([('planned', 'Planned'), ('done', 'Completed'), ('action', 'Action Required'), ('closed', 'Closed')], default='planned', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('garment.compliance.fire.drill') or 'New'
        return super().create(vals_list)

    def action_complete(self):
        for rec in self:
            rec.state = 'action' if rec.issues or rec.corrective_action else 'done'

    def action_close(self):
        self.write({'state': 'closed'})


class GarmentComplianceEquipment(models.Model):
    _name = 'garment.compliance.equipment'
    _description = 'Compliance / Safety Equipment Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_inspection_date asc, name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default='New', copy=False, readonly=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    equipment_type = fields.Selection([
        ('fire_extinguisher', 'Fire Extinguisher'), ('fire_alarm', 'Fire Alarm'), ('emergency_light', 'Emergency Light'),
        ('fire_door', 'Fire Door'), ('first_aid', 'First Aid'), ('electrical', 'Electrical Equipment'),
        ('boiler', 'Boiler'), ('generator', 'Generator'), ('lift', 'Lift'), ('compressor', 'Compressor'),
        ('machine', 'Machine Safety'), ('ppe', 'PPE'), ('other', 'Other')
    ], required=True, default='other')
    department_id = fields.Many2one('hr.department')
    location = fields.Char(required=True)
    serial_no = fields.Char()
    install_date = fields.Date()
    inspection_frequency_days = fields.Integer(default=30)
    last_inspection_date = fields.Date()
    next_inspection_date = fields.Date(tracking=True)
    certificate_expiry_date = fields.Date()
    responsible_id = fields.Many2one('res.users', tracking=True)
    condition = fields.Selection([('good', 'Good'), ('attention', 'Needs Attention'), ('unsafe', 'Unsafe')], default='good', tracking=True)
    state = fields.Selection([('active', 'Active'), ('due', 'Inspection Due'), ('expired', 'Certificate Expired'), ('out', 'Out of Service')], default='active', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Certificates / Photos')
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = seq.next_by_code('garment.compliance.equipment') or 'New'
        return super().create(vals_list)

    @api.onchange('last_inspection_date', 'inspection_frequency_days')
    def _onchange_next_inspection(self):
        if self.last_inspection_date and self.inspection_frequency_days:
            self.next_inspection_date = self.last_inspection_date + timedelta(days=self.inspection_frequency_days)

    def action_mark_inspected(self):
        today = fields.Date.context_today(self)
        summary = _('Equipment inspection / certificate attention required')
        for rec in self:
            rec.last_inspection_date = today
            rec.next_inspection_date = today + timedelta(days=rec.inspection_frequency_days or 0) if rec.inspection_frequency_days else False
            rec.state = 'active'
            activities = self.env['mail.activity'].search([
                ('res_model', '=', self._name), ('res_id', '=', rec.id), ('summary', '=', summary)
            ])
            if activities:
                activities.action_feedback(feedback=_('Equipment inspection completed.'))

    @api.model
    def _cron_check_due(self):
        today = fields.Date.context_today(self)
        warning = today + timedelta(days=7)
        for rec in self.search([('state', '!=', 'out')]):
            new_state = 'active'
            if rec.certificate_expiry_date and rec.certificate_expiry_date < today:
                new_state = 'expired'
            elif rec.next_inspection_date and rec.next_inspection_date <= warning:
                new_state = 'due'
            rec.state = new_state
            if new_state in ('due', 'expired') and rec.responsible_id:
                summary = _('Equipment inspection / certificate attention required')
                exists = self.env['mail.activity'].search_count([
                    ('res_model', '=', self._name), ('res_id', '=', rec.id),
                    ('user_id', '=', rec.responsible_id.id), ('summary', '=', summary)
                ])
                if not exists:
                    deadline = (rec.certificate_expiry_date if new_state == 'expired' else rec.next_inspection_date) or today
                    rec.activity_schedule('mail.mail_activity_data_todo', user_id=rec.responsible_id.id,
                                          date_deadline=deadline, summary=summary)


class ResCompanyGarmentComplianceDashboard(models.Model):
    _inherit = 'res.company'

    gc_requirement_total = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_compliant = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_non_compliant = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_expiring = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_open_capa = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_overdue_capa = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_critical_findings = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_upcoming_audits = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_equipment_due = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_training_due = fields.Integer(compute='_compute_garment_compliance_kpis')
    gc_workhour_rate = fields.Float(compute='_compute_garment_compliance_kpis', digits=(16, 2))
    gc_wage_rate = fields.Float(compute='_compute_garment_compliance_kpis', digits=(16, 2))

    def _compute_garment_compliance_kpis(self):
        today = fields.Date.context_today(self)
        next_30 = today + timedelta(days=30)
        for company in self:
            req = self.env['garment.compliance.requirement']
            capa = self.env['garment.compliance.capa']
            finding = self.env['garment.compliance.finding']
            audit = self.env['garment.compliance.audit']
            equip = self.env['garment.compliance.equipment']
            training = self.env['garment.compliance.training']
            wh = self.env['garment.compliance.workhour.review']
            wage = self.env['garment.compliance.wage.review']

            base = [('company_id', '=', company.id)]
            company.gc_requirement_total = req.search_count(base)
            company.gc_compliant = req.search_count(base + [('state', '=', 'compliant')])
            company.gc_non_compliant = req.search_count(base + [('state', 'in', ['non_compliant', 'expired'])])
            company.gc_expiring = req.search_count(base + [('state', '=', 'expiring')])
            company.gc_open_capa = capa.search_count(base + [('state', '!=', 'closed')])
            company.gc_overdue_capa = capa.search_count(base + [('state', '!=', 'closed'), ('due_date', '<', today)])
            company.gc_critical_findings = finding.search_count(base + [('severity', '=', 'critical'), ('state', '!=', 'closed')])
            company.gc_upcoming_audits = audit.search_count(base + [('next_audit_date', '>=', today), ('next_audit_date', '<=', next_30)])
            company.gc_equipment_due = equip.search_count(base + [('state', 'in', ['due', 'expired'])])
            company.gc_training_due = training.search_count(base + [('next_training_date', '>=', today), ('next_training_date', '<=', next_30)])

            latest_wh = wh.search(base + [('state', 'in', ['reviewed', 'closed'])], order='date_to desc, id desc', limit=1)
            latest_wage = wage.search(base + [('state', 'in', ['reviewed', 'closed'])], order='period_end desc, id desc', limit=1)
            company.gc_workhour_rate = latest_wh.compliance_rate if latest_wh else 0.0
            company.gc_wage_rate = latest_wage.compliance_rate if latest_wage else 0.0
