"""
Professional PDF Generator v2 for Grant Applications

Generates consulting-firm quality grant application PDFs with:
- Professional cover page with branding
- Table of contents with page numbers
- Proper headers and footers
- Professional typography and formatting
- Budget tables with proper structure
- Quality indicators and completeness scoring
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
    HRFlowable, PageBreak, KeepTogether, ListFlowable, ListItem
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from sqlalchemy.orm import Session

from app.models import (
    Application, ApplicationSection, SectionType,
    UserProfile, OrganizationProfile, GrantProgram,
    BudgetLineItem, BudgetCategory
)


# Professional color scheme
COLORS = {
    "primary": colors.HexColor("#0d9488"),  # Teal
    "secondary": colors.HexColor("#1e3a5f"),  # Navy
    "accent": colors.HexColor("#059669"),  # Green
    "text_dark": colors.HexColor("#1f2937"),
    "text_light": colors.HexColor("#6b7280"),
    "border": colors.HexColor("#e5e7eb"),
    "background_light": colors.HexColor("#f9fafb"),
    "background_accent": colors.HexColor("#f0fdfa"),
}


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    if not amount:
        return "$0"
    return f"${amount:,.0f}"


class ProfessionalPDFGenerator:
    """
    Generates consulting-firm quality grant application PDFs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.page_count = 0
        self.current_page = 0

    def generate_professional_application_pdf(
        self,
        application_id: str
    ) -> bytes:
        """
        Generate a complete professional application PDF.

        Args:
            application_id: The application to generate PDF for

        Returns:
            PDF bytes
        """
        # Load all data
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()

        if not application:
            raise ValueError(f"Application {application_id} not found")

        program = application.program
        user_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == application.user_id
        ).first()
        org_profile = self.db.query(OrganizationProfile).filter(
            OrganizationProfile.user_id == application.user_id
        ).first()
        sections = self.db.query(ApplicationSection).filter(
            ApplicationSection.application_id == application_id
        ).order_by(ApplicationSection.section_type).all()
        budget_items = self.db.query(BudgetLineItem).filter(
            BudgetLineItem.application_id == application_id
        ).order_by(BudgetLineItem.category, BudgetLineItem.sort_order).all()

        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=1*inch,
            leftMargin=1*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )

        # Create styles
        styles = self._create_styles()

        # Build story
        story = []

        # Cover Page
        story.extend(self._create_cover_page(
            application, program, user_profile, org_profile, styles
        ))
        story.append(PageBreak())

        # Table of Contents Page
        story.extend(self._create_toc_placeholder(styles))
        story.append(PageBreak())

        # Executive Summary (if exists)
        exec_section = next(
            (s for s in sections if s.section_type == SectionType.EXECUTIVE_SUMMARY),
            None
        )
        if exec_section and exec_section.content:
            story.extend(self._create_section(
                "Executive Summary",
                exec_section.content,
                styles,
                show_quality=True,
                quality_score=exec_section.quality_score
            ))
            story.append(PageBreak())

        # Main Sections
        section_order = [
            SectionType.ORGANIZATIONAL_BACKGROUND,
            SectionType.STATEMENT_OF_NEED,
            SectionType.PROJECT_DESCRIPTION,
            SectionType.GOALS_OBJECTIVES,
            SectionType.EVALUATION_PLAN,
            SectionType.BUDGET_NARRATIVE,
            SectionType.SUSTAINABILITY_PLAN,
        ]

        for section_type in section_order:
            section = next(
                (s for s in sections if s.section_type == section_type),
                None
            )
            if section and section.content:
                title = section_type.value.replace("_", " ").title()
                story.extend(self._create_section(
                    title,
                    section.content,
                    styles,
                    show_quality=True,
                    quality_score=section.quality_score
                ))

        # Budget Section with Tables
        if budget_items:
            story.append(PageBreak())
            story.extend(self._create_budget_section(budget_items, styles))

        # Appendix: Application Summary
        story.append(PageBreak())
        story.extend(self._create_appendix_summary(
            application, program, user_profile, org_profile, sections, styles
        ))

        # Build PDF with page numbers
        doc.build(
            story,
            onFirstPage=self._add_page_number,
            onLaterPages=self._add_page_number
        )

        buffer.seek(0)
        return buffer.getvalue()

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create professional paragraph styles."""
        base_styles = getSampleStyleSheet()

        custom_styles = {}

        # Cover page styles
        custom_styles["CoverTitle"] = ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Heading1"],
            fontSize=28,
            textColor=COLORS["secondary"],
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName="Helvetica-Bold"
        )

        custom_styles["CoverSubtitle"] = ParagraphStyle(
            "CoverSubtitle",
            parent=base_styles["Normal"],
            fontSize=14,
            textColor=COLORS["primary"],
            alignment=TA_CENTER,
            spaceAfter=8
        )

        custom_styles["CoverInfo"] = ParagraphStyle(
            "CoverInfo",
            parent=base_styles["Normal"],
            fontSize=11,
            textColor=COLORS["text_dark"],
            alignment=TA_CENTER,
            spaceAfter=6
        )

        # TOC styles
        custom_styles["TOCTitle"] = ParagraphStyle(
            "TOCTitle",
            parent=base_styles["Heading1"],
            fontSize=18,
            textColor=COLORS["secondary"],
            alignment=TA_LEFT,
            spaceAfter=24,
            fontName="Helvetica-Bold"
        )

        custom_styles["TOCEntry"] = ParagraphStyle(
            "TOCEntry",
            parent=base_styles["Normal"],
            fontSize=11,
            textColor=COLORS["text_dark"],
            leftIndent=0,
            spaceAfter=8
        )

        # Section styles
        custom_styles["SectionTitle"] = ParagraphStyle(
            "SectionTitle",
            parent=base_styles["Heading1"],
            fontSize=16,
            textColor=COLORS["secondary"],
            spaceBefore=18,
            spaceAfter=12,
            fontName="Helvetica-Bold",
            borderWidth=0,
            borderPadding=0,
            borderColor=None,
            borderRadius=None
        )

        custom_styles["SectionSubtitle"] = ParagraphStyle(
            "SectionSubtitle",
            parent=base_styles["Heading2"],
            fontSize=12,
            textColor=COLORS["primary"],
            spaceBefore=14,
            spaceAfter=8,
            fontName="Helvetica-Bold"
        )

        # Body text - professional 11pt justified
        custom_styles["BodyText"] = ParagraphStyle(
            "BodyText",
            parent=base_styles["Normal"],
            fontSize=11,
            textColor=COLORS["text_dark"],
            alignment=TA_JUSTIFY,
            leading=16,
            spaceBefore=0,
            spaceAfter=8,
            firstLineIndent=0
        )

        custom_styles["BodyTextIndent"] = ParagraphStyle(
            "BodyTextIndent",
            parent=custom_styles["BodyText"],
            leftIndent=24
        )

        # Caption / small text
        custom_styles["Caption"] = ParagraphStyle(
            "Caption",
            parent=base_styles["Normal"],
            fontSize=9,
            textColor=COLORS["text_light"],
            alignment=TA_CENTER,
            spaceAfter=6
        )

        custom_styles["SmallText"] = ParagraphStyle(
            "SmallText",
            parent=base_styles["Normal"],
            fontSize=9,
            textColor=COLORS["text_light"]
        )

        # Quality badge
        custom_styles["QualityBadge"] = ParagraphStyle(
            "QualityBadge",
            parent=base_styles["Normal"],
            fontSize=9,
            textColor=COLORS["accent"],
            alignment=TA_RIGHT
        )

        # Table styles
        custom_styles["TableHeader"] = ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontSize=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT
        )

        custom_styles["TableCell"] = ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontSize=10,
            textColor=COLORS["text_dark"]
        )

        custom_styles["TableCellRight"] = ParagraphStyle(
            "TableCellRight",
            parent=custom_styles["TableCell"],
            alignment=TA_RIGHT
        )

        return custom_styles

    def _create_cover_page(
        self,
        application: Application,
        program: GrantProgram,
        user_profile: Optional[UserProfile],
        org_profile: Optional[OrganizationProfile],
        styles: Dict
    ) -> List:
        """Create professional cover page."""
        story = []

        # Top spacing
        story.append(Spacer(1, 1.5*inch))

        # Organization name
        org_name = "Applicant"
        if user_profile:
            org_name = user_profile.organization_name or user_profile.full_name or "Applicant"
        story.append(Paragraph(org_name, styles["CoverSubtitle"]))
        story.append(Spacer(1, 0.3*inch))

        # Horizontal line
        story.append(HRFlowable(
            width="80%",
            thickness=2,
            color=COLORS["primary"],
            hAlign="CENTER"
        ))
        story.append(Spacer(1, 0.3*inch))

        # Grant program name
        program_name = program.name if program else "Grant Application"
        story.append(Paragraph(program_name, styles["CoverTitle"]))

        # Agency
        if program and program.agency:
            story.append(Paragraph(program.agency, styles["CoverSubtitle"]))

        story.append(Spacer(1, 0.5*inch))

        # Funding amount (if budget exists)
        budget_total = sum(
            (item.unit_cost or 0) * (item.quantity or 1)
            for item in (application.budget_line_items or [])
            if not item.is_matching
        )
        if budget_total > 0:
            story.append(Paragraph(
                f"Funding Request: {format_currency(budget_total)}",
                styles["CoverInfo"]
            ))

        story.append(Spacer(1, 1*inch))

        # Submission date
        story.append(Paragraph(
            f"Application Date: {datetime.now().strftime('%B %d, %Y')}",
            styles["CoverInfo"]
        ))

        # Contact information
        if user_profile:
            story.append(Spacer(1, 0.5*inch))

            contact_info = []
            if user_profile.full_name:
                contact_info.append(user_profile.full_name)
            if user_profile.city and user_profile.state:
                contact_info.append(f"{user_profile.city}, {user_profile.state}")
            if user_profile.phone:
                contact_info.append(user_profile.phone)
            if user_profile.website:
                contact_info.append(user_profile.website)

            for info in contact_info:
                story.append(Paragraph(info, styles["CoverInfo"]))

        # Bottom spacing with draft watermark
        story.append(Spacer(1, 1*inch))
        if application.status.value in ["draft", "in_progress"]:
            story.append(Paragraph(
                "DRAFT - FOR REVIEW PURPOSES ONLY",
                ParagraphStyle(
                    "Watermark",
                    fontSize=14,
                    textColor=colors.HexColor("#dc2626"),
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold"
                )
            ))

        return story

    def _create_toc_placeholder(self, styles: Dict) -> List:
        """Create table of contents placeholder."""
        story = []

        story.append(Paragraph("Table of Contents", styles["TOCTitle"]))
        story.append(Spacer(1, 0.3*inch))

        # Static TOC entries (page numbers would need a two-pass build)
        toc_entries = [
            ("Executive Summary", 3),
            ("Organizational Background", 4),
            ("Statement of Need", 5),
            ("Project Description", 6),
            ("Goals and Objectives", 8),
            ("Evaluation Plan", 9),
            ("Budget Narrative", 10),
            ("Sustainability Plan", 11),
            ("Detailed Budget", 12),
            ("Application Summary", 13),
        ]

        for title, page in toc_entries:
            # Create dotted line effect
            dots = "." * 60
            entry = f"{title} {dots} {page}"
            story.append(Paragraph(entry[:70], styles["TOCEntry"]))

        return story

    def _create_section(
        self,
        title: str,
        content: str,
        styles: Dict,
        show_quality: bool = False,
        quality_score: Optional[float] = None
    ) -> List:
        """Create a formatted section with content."""
        story = []

        # Section title with optional quality badge
        if show_quality and quality_score is not None:
            # Title row with quality score
            title_table = Table(
                [[
                    Paragraph(title, styles["SectionTitle"]),
                    Paragraph(
                        f"Quality Score: {quality_score:.0f}/100",
                        styles["QualityBadge"]
                    )
                ]],
                colWidths=[4.5*inch, 2*inch]
            )
            title_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]))
            story.append(title_table)
        else:
            story.append(Paragraph(title, styles["SectionTitle"]))

        # Decorative line under title
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=COLORS["primary"]
        ))
        story.append(Spacer(1, 12))

        # Content - split into paragraphs
        if content:
            paragraphs = content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    # Check for bullet points
                    if para.strip().startswith("- ") or para.strip().startswith("• "):
                        lines = para.strip().split("\n")
                        bullet_items = []
                        for line in lines:
                            clean_line = line.strip().lstrip("-•").strip()
                            if clean_line:
                                bullet_items.append(
                                    ListItem(Paragraph(clean_line, styles["BodyText"]))
                                )
                        if bullet_items:
                            story.append(ListFlowable(
                                bullet_items,
                                bulletType="bullet",
                                leftIndent=24,
                                bulletFontSize=8
                            ))
                    # Check for numbered lists
                    elif para.strip()[0].isdigit() and para.strip()[1] in ".):":
                        lines = para.strip().split("\n")
                        for line in lines:
                            story.append(Paragraph(line.strip(), styles["BodyTextIndent"]))
                    else:
                        story.append(Paragraph(para.strip(), styles["BodyText"]))

        story.append(Spacer(1, 12))

        return story

    def _create_budget_section(
        self,
        budget_items: List[BudgetLineItem],
        styles: Dict
    ) -> List:
        """Create professional budget tables."""
        story = []

        story.append(Paragraph("Detailed Budget", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS["primary"]))
        story.append(Spacer(1, 12))

        # Group by category
        categories: Dict[str, List] = {}
        for item in budget_items:
            cat = item.category.value if item.category else "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        grand_total_request = 0
        grand_total_match = 0

        for category, items in categories.items():
            # Category header
            story.append(Paragraph(
                category.replace("_", " ").title(),
                styles["SectionSubtitle"]
            ))

            # Table header
            table_data = [[
                Paragraph("Description", styles["TableHeader"]),
                Paragraph("Unit Cost", styles["TableHeader"]),
                Paragraph("Qty", styles["TableHeader"]),
                Paragraph("Total", styles["TableHeader"]),
                Paragraph("Match", styles["TableHeader"]),
            ]]

            category_total = 0
            category_match = 0

            for item in items:
                total = (item.unit_cost or 0) * (item.quantity or 1)
                if item.is_matching:
                    category_match += total
                else:
                    category_total += total

                table_data.append([
                    Paragraph(item.description[:40], styles["TableCell"]),
                    Paragraph(format_currency(item.unit_cost or 0), styles["TableCellRight"]),
                    Paragraph(str(int(item.quantity or 1)), styles["TableCellRight"]),
                    Paragraph(format_currency(total), styles["TableCellRight"]),
                    Paragraph("Yes" if item.is_matching else "", styles["TableCell"]),
                ])

            # Category subtotal
            table_data.append([
                Paragraph("<b>Subtotal</b>", styles["TableCell"]),
                "", "",
                Paragraph(f"<b>{format_currency(category_total)}</b>", styles["TableCellRight"]),
                Paragraph(f"<b>{format_currency(category_match)}</b>" if category_match else "", styles["TableCellRight"]),
            ])

            grand_total_request += category_total
            grand_total_match += category_match

            # Create table
            table = Table(
                table_data,
                colWidths=[2.5*inch, 1.2*inch, 0.6*inch, 1.2*inch, 0.8*inch]
            )
            table.setStyle(TableStyle([
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["secondary"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                # All cells
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                # Subtotal row
                ("BACKGROUND", (0, -1), (-1, -1), COLORS["background_light"]),
                # Right align numbers
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]))

            story.append(table)
            story.append(Spacer(1, 16))

        # Grand total table
        story.append(Spacer(1, 12))
        grand_total_data = [
            ["Total Grant Request:", format_currency(grand_total_request)],
            ["Total Match/Cost Share:", format_currency(grand_total_match)],
            ["Grand Total:", format_currency(grand_total_request + grand_total_match)],
        ]

        grand_table = Table(
            grand_total_data,
            colWidths=[4*inch, 2*inch]
        )
        grand_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, -1), (1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, -1), (-1, -1), COLORS["background_accent"]),
            ("BOX", (0, 0), (-1, -1), 1, COLORS["primary"]),
        ]))

        story.append(grand_table)

        return story

    def _create_appendix_summary(
        self,
        application: Application,
        program: GrantProgram,
        user_profile: Optional[UserProfile],
        org_profile: Optional[OrganizationProfile],
        sections: List[ApplicationSection],
        styles: Dict
    ) -> List:
        """Create application summary appendix."""
        story = []

        story.append(Paragraph("Appendix: Application Summary", styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS["primary"]))
        story.append(Spacer(1, 12))

        # Application metadata
        summary_data = [
            ["Application ID:", application.id[:8] + "..."],
            ["Status:", application.status.value.replace("_", " ").title()],
            ["Completeness:", f"{application.completeness_score or 0:.0f}%"],
            ["Created:", application.created_at.strftime("%Y-%m-%d") if application.created_at else "N/A"],
            ["Last Updated:", application.updated_at.strftime("%Y-%m-%d") if application.updated_at else "N/A"],
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Section quality scores
        if sections:
            story.append(Paragraph("Section Quality Scores", styles["SectionSubtitle"]))
            story.append(Spacer(1, 8))

            scores_data = [["Section", "Word Count", "Quality Score"]]
            for section in sorted(sections, key=lambda s: s.section_type.value):
                scores_data.append([
                    section.section_type.value.replace("_", " ").title(),
                    str(section.word_count or 0),
                    f"{section.quality_score:.0f}" if section.quality_score else "N/A"
                ])

            scores_table = Table(scores_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            scores_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["secondary"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(scores_table)

        # Footer
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS["border"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "Generated by GrantsAssist Professional Grant Writing System",
            styles["Caption"]
        ))
        story.append(Paragraph(
            f"Document generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            styles["Caption"]
        ))

        return story

    def _add_page_number(self, canvas, doc):
        """Add page numbers to footer."""
        page_num = canvas.getPageNumber()
        if page_num > 1:  # Skip cover page
            text = f"Page {page_num}"
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(COLORS["text_light"])
            canvas.drawCentredString(letter[0]/2, 0.5*inch, text)
            canvas.restoreState()


def create_professional_pdf_generator(db: Session) -> ProfessionalPDFGenerator:
    """Create a new ProfessionalPDFGenerator instance."""
    return ProfessionalPDFGenerator(db)
