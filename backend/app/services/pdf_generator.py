"""
PDF Generation Service for Grant Applications

Generates:
1. Grant Summary PDFs - Overview of a grant program
2. Application Draft PDFs - User's application with generated narratives
3. Eligibility Report PDFs - Personalized eligibility analysis
"""

import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.database import GrantProgram, Application, UserProfile


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.0f}K"
    return f"${amount:,.0f}"


def generate_grant_summary_pdf(program: GrantProgram) -> bytes:
    """
    Generate a summary PDF for a grant program.

    Args:
        program: GrantProgram model instance

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='GrantTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=6,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='GrantSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0d9488'),
        spaceBefore=12,
        spaceAfter=6,
        borderPadding=4,
        backColor=colors.HexColor('#f0fdfa')
    ))
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280')
    ))

    story = []

    # Header
    story.append(Paragraph(program.name, styles['GrantTitle']))
    story.append(Paragraph(f"Agency: {program.agency or 'N/A'}", styles['GrantSubtitle']))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        styles['SmallText']
    ))
    story.append(Spacer(1, 12))

    # Quick Facts
    story.append(Paragraph("Quick Facts", styles['SectionHeader']))

    funding_range = "N/A"
    if program.min_award and program.max_award:
        funding_range = f"{format_currency(program.min_award)} - {format_currency(program.max_award)}"
    elif program.max_award:
        funding_range = f"Up to {format_currency(program.max_award)}"

    deadline_str = "Rolling / Open" if program.rolling_deadline else (
        program.deadline.strftime('%B %d, %Y') if program.deadline else "TBD"
    )

    match_str = f"{int(program.match_required * 100)}%" if program.match_required else "None required"

    facts_data = [
        ["Category:", program.category.value.replace('_', ' ').title() if program.category else "N/A"],
        ["Funding Range:", funding_range],
        ["Match Required:", match_str],
        ["Deadline:", deadline_str],
    ]

    facts_table = Table(facts_data, colWidths=[1.5*inch, 5*inch])
    facts_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(facts_table)
    story.append(Spacer(1, 12))

    # Description
    if program.description:
        story.append(Paragraph("Program Overview", styles['SectionHeader']))
        story.append(Paragraph(program.description, styles['BodyText']))
        story.append(Spacer(1, 8))

    # Eligibility
    if program.eligibility_summary:
        story.append(Paragraph("Eligibility Requirements", styles['SectionHeader']))
        story.append(Paragraph(program.eligibility_summary, styles['BodyText']))
        story.append(Spacer(1, 8))

    # Links
    if program.program_url or program.application_url:
        story.append(Paragraph("Resources", styles['SectionHeader']))
        if program.program_url:
            story.append(Paragraph(f"Program Info: {program.program_url}", styles['SmallText']))
        if program.application_url:
            story.append(Paragraph(f"Apply: {program.application_url}", styles['SmallText']))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This summary is for informational purposes. Please verify all details with the granting agency.",
        styles['SmallText']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_application_pdf(
    application: Application,
    profile: Optional[UserProfile] = None,
    program: Optional[GrantProgram] = None,
    narratives: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Generate a draft application PDF.

    Args:
        application: Application model instance
        profile: User's profile data
        program: Grant program details
        narratives: Generated narrative sections

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='AppTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=4,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='AppSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='AppSection',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0d9488'),
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='AppBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    ))
    styles.add(ParagraphStyle(
        name='AppLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280')
    ))

    story = []

    # Cover Page
    program_name = program.name if program else "Grant Application"
    story.append(Paragraph(f"Draft Application", styles['AppTitle']))
    story.append(Paragraph(program_name, styles['AppSubtitle']))
    story.append(Spacer(1, 8))

    # Status badge
    status_text = f"Status: {application.status.value.replace('_', ' ').title()}"
    story.append(Paragraph(status_text, styles['AppLabel']))
    story.append(Paragraph(
        f"Last Updated: {application.updated_at.strftime('%B %d, %Y') if application.updated_at else 'N/A'}",
        styles['AppLabel']
    ))
    story.append(Spacer(1, 16))

    # Applicant Information
    if profile:
        story.append(Paragraph("Applicant Information", styles['AppSection']))

        applicant_data = []
        if profile.full_name:
            applicant_data.append(["Name:", profile.full_name])
        if profile.organization_name:
            applicant_data.append(["Organization:", profile.organization_name])
        if profile.organization_type:
            applicant_data.append(["Org Type:", profile.organization_type.replace('_', ' ').title()])
        if profile.address:
            address = f"{profile.address}, {profile.city}, {profile.state} {profile.zip_code}"
            applicant_data.append(["Address:", address])
        if profile.ein:
            applicant_data.append(["EIN:", profile.ein])
        if profile.uei_number:
            applicant_data.append(["UEI:", profile.uei_number])

        if applicant_data:
            app_table = Table(applicant_data, colWidths=[1.3*inch, 5*inch])
            app_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(app_table)
        story.append(Spacer(1, 8))

    # Narrative Sections
    if narratives:
        for section_name, content in narratives.items():
            if content:
                # Convert section key to title
                title = section_name.replace('_', ' ').title()
                story.append(Paragraph(title, styles['AppSection']))
                story.append(Paragraph(content, styles['AppBody']))

    # If we have generated narrative from the application
    if application.generated_narrative and not narratives:
        story.append(Paragraph("Project Narrative", styles['AppSection']))
        story.append(Paragraph(application.generated_narrative, styles['AppBody']))

    # Completeness
    story.append(Spacer(1, 16))
    story.append(Paragraph("Application Status", styles['AppSection']))
    completeness = application.completeness_score or 0
    story.append(Paragraph(
        f"Completeness: {completeness:.0f}%",
        styles['AppBody']
    ))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "DRAFT - This document is for review purposes only. "
        "Final submission must be made through the official application portal.",
        ParagraphStyle('Footer', parent=styles['AppLabel'], alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_eligibility_report_pdf(
    profile: UserProfile,
    eligible_programs: List[GrantProgram],
    match_scores: Optional[Dict[str, float]] = None
) -> bytes:
    """
    Generate an eligibility report PDF showing matching programs.

    Args:
        profile: User's profile
        eligible_programs: List of matching grant programs
        match_scores: Dict of program_id -> match score (0-100)

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=6,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='ReportSection',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0d9488'),
        spaceBefore=12,
        spaceAfter=6,
        backColor=colors.HexColor('#f0fdfa')
    ))
    styles.add(ParagraphStyle(
        name='ReportBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    ))
    styles.add(ParagraphStyle(
        name='ProgramName',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#059669'),
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='ReportSmall',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280')
    ))

    story = []

    # Header
    org_name = profile.organization_name or profile.full_name or "Your Organization"
    story.append(Paragraph("Grant Eligibility Report", styles['ReportTitle']))
    story.append(Paragraph(f"Prepared for: {org_name}", styles['ReportSubtitle']))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        styles['ReportSmall']
    ))
    story.append(Spacer(1, 12))

    # Profile Summary
    story.append(Paragraph("Your Profile", styles['ReportSection']))

    profile_items = []
    if profile.organization_type:
        profile_items.append(["Type:", profile.organization_type.replace('_', ' ').title()])
    if profile.state:
        profile_items.append(["Location:", f"{profile.city or ''}, {profile.state}"])
    if profile.annual_revenue:
        profile_items.append(["Annual Revenue:", format_currency(profile.annual_revenue)])
    if profile.employee_count:
        profile_items.append(["Employees:", str(profile.employee_count)])

    # Add demographic qualifiers
    qualifiers = []
    if profile.is_veteran:
        qualifiers.append("Veteran-Owned")
    if profile.is_minority_owned:
        qualifiers.append("Minority-Owned")
    if profile.is_woman_owned:
        qualifiers.append("Woman-Owned")
    if profile.is_rural:
        qualifiers.append("Rural Area")
    if qualifiers:
        profile_items.append(["Qualifications:", ", ".join(qualifiers)])

    if profile_items:
        prof_table = Table(profile_items, colWidths=[1.5*inch, 5*inch])
        prof_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(prof_table)
    story.append(Spacer(1, 12))

    # Matching Programs
    story.append(Paragraph(f"Matching Programs ({len(eligible_programs)})", styles['ReportSection']))

    if not eligible_programs:
        story.append(Paragraph(
            "No matching programs found based on your current profile. "
            "Try updating your profile with more details to see available grants.",
            styles['ReportBody']
        ))
    else:
        for program in eligible_programs:
            story.append(Spacer(1, 8))

            # Match score if available
            score_text = ""
            if match_scores and program.id in match_scores:
                score = match_scores[program.id]
                score_text = f" ({score:.0f}% match)"

            story.append(Paragraph(f"✓ {program.name}{score_text}", styles['ProgramName']))

            # Program details
            funding = "Varies"
            if program.min_award and program.max_award:
                funding = f"{format_currency(program.min_award)} - {format_currency(program.max_award)}"

            deadline = "Rolling" if program.rolling_deadline else (
                program.deadline.strftime('%B %d, %Y') if program.deadline else "TBD"
            )

            details = [
                ["Agency:", program.agency or "N/A"],
                ["Funding:", funding],
                ["Deadline:", deadline],
            ]

            det_table = Table(details, colWidths=[1*inch, 4*inch])
            det_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(det_table)

            if program.description:
                desc = program.description[:200] + "..." if len(program.description) > 200 else program.description
                story.append(Paragraph(desc, ParagraphStyle(
                    'ProgDesc', parent=styles['ReportSmall'], leftIndent=20
                )))

    # Next Steps
    story.append(Spacer(1, 16))
    story.append(Paragraph("Next Steps", styles['ReportSection']))
    steps = [
        "1. Review each program's eligibility requirements in detail",
        "2. Ensure your SAM.gov registration is current (required for federal grants)",
        "3. Gather required documents: EIN, UEI, financial statements",
        "4. Start your application in the GrantsAssist app",
    ]
    for step in steps:
        story.append(Paragraph(step, styles['ReportBody']))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This report is based on publicly available program information and your profile data. "
        "Final eligibility is determined by the granting agency.",
        styles['ReportSmall']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
