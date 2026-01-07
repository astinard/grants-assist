"""
Context Assembler for Professional Grant Writing

Gathers all relevant data from user profile, organization profile,
prior grants, achievements, and community data to provide rich context
for AI-powered grant narrative generation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import (
    User, UserProfile, OrganizationProfile, PriorGrant,
    Achievement, CommunityData, BudgetLineItem, Application,
    GrantProgram, PriorGrantStatus
)

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    Assembles comprehensive context for professional grant writing.
    Gathers data from multiple sources to provide AI with rich context.
    """

    def __init__(self, db: Session):
        self.db = db

    def assemble_full_context(
        self,
        user_id: str,
        application_id: str,
        program_id: str
    ) -> Dict[str, Any]:
        """
        Assemble complete context for grant narrative generation.

        Returns a comprehensive dictionary with all available information
        about the organization, its history, achievements, community needs,
        and the specific grant program being applied for.
        """
        context = {
            "organization": self._get_organization_context(user_id),
            "prior_grants": self._get_prior_grants_context(user_id),
            "achievements": self._get_achievements_context(user_id),
            "community_data": self._get_community_data_context(user_id),
            "budget": self._get_budget_context(application_id),
            "program": self._get_program_context(program_id),
            "application": self._get_application_context(application_id),
        }

        # Add computed fields for easier prompt building
        context["summary"] = self._build_context_summary(context)

        return context

    def _get_organization_context(self, user_id: str) -> Dict[str, Any]:
        """Get organization profile and basic user profile data."""
        user_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        org_profile = self.db.query(OrganizationProfile).filter(
            OrganizationProfile.user_id == user_id
        ).first()

        org_context = {
            # Basic Info
            "name": "",
            "type": "",
            "location": "",
            "full_address": "",

            # Mission & History
            "mission_statement": "",
            "vision_statement": "",
            "founding_year": None,
            "years_in_operation": None,

            # Service Area
            "service_area": "",
            "service_area_population": None,
            "geographic_reach": "",

            # Capacity
            "annual_budget": None,
            "annual_revenue": None,
            "staff_count": None,
            "volunteer_count": None,
            "board_size": None,
            "employee_count": None,

            # Credentials
            "certifications": [],
            "accreditations": [],
            "key_partnerships": [],

            # Federal IDs
            "ein": "",
            "uei_number": "",
            "sam_registered": False,

            # Demographics
            "is_veteran": False,
            "is_minority_owned": False,
            "is_woman_owned": False,
            "is_rural": False,

            # Impact
            "clients_served_annually": None,
            "programs_offered": [],

            # Contact
            "contact_name": "",
            "phone": "",
            "website": "",
        }

        if user_profile:
            org_context.update({
                "name": user_profile.organization_name or user_profile.full_name or "",
                "type": user_profile.organization_type or "",
                "location": f"{user_profile.city or ''}, {user_profile.state or ''}".strip(", "),
                "full_address": self._format_address(user_profile),
                "years_in_operation": user_profile.years_in_operation,
                "annual_revenue": user_profile.annual_revenue,
                "employee_count": user_profile.employee_count,
                "ein": user_profile.ein or "",
                "uei_number": user_profile.uei_number or "",
                "sam_registered": user_profile.sam_registered or False,
                "is_veteran": user_profile.is_veteran or False,
                "is_minority_owned": user_profile.is_minority_owned or False,
                "is_woman_owned": user_profile.is_woman_owned or False,
                "is_rural": user_profile.is_rural or False,
                "contact_name": user_profile.full_name or "",
                "phone": user_profile.phone or "",
                "website": user_profile.website or "",
            })

        if org_profile:
            org_context.update({
                "mission_statement": org_profile.mission_statement or "",
                "vision_statement": org_profile.vision_statement or "",
                "founding_year": org_profile.founding_year,
                "service_area": org_profile.service_area or "",
                "service_area_population": org_profile.service_area_population,
                "geographic_reach": org_profile.geographic_reach or "",
                "annual_budget": org_profile.annual_budget,
                "staff_count": org_profile.staff_count,
                "volunteer_count": org_profile.volunteer_count,
                "board_size": org_profile.board_size,
                "clients_served_annually": org_profile.clients_served_annually,
                "certifications": self._parse_json_field(org_profile.certifications),
                "accreditations": self._parse_json_field(org_profile.accreditations),
                "key_partnerships": self._parse_json_field(org_profile.key_partnerships),
                "programs_offered": self._parse_json_field(org_profile.programs_offered),
            })

        return org_context

    def _get_prior_grants_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Get prior grant history for credibility."""
        prior_grants = self.db.query(PriorGrant).filter(
            PriorGrant.user_id == user_id
        ).order_by(PriorGrant.year_awarded.desc()).all()

        return [
            {
                "funder_name": grant.funder_name,
                "grant_title": grant.grant_title or "",
                "amount": grant.amount,
                "year": grant.year_awarded,
                "status": grant.status.value if grant.status else "awarded",
                "outcomes_achieved": grant.outcomes_achieved or "",
                "metrics_achieved": self._parse_json_field(grant.metrics_achieved),
                "lessons_learned": grant.lessons_learned or "",
            }
            for grant in prior_grants
        ]

    def _get_achievements_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Get organizational achievements."""
        achievements = self.db.query(Achievement).filter(
            Achievement.user_id == user_id
        ).order_by(Achievement.year.desc()).all()

        return [
            {
                "title": ach.title,
                "description": ach.description or "",
                "category": ach.category or "",
                "metric_value": ach.metric_value,
                "metric_unit": ach.metric_unit or "",
                "year": ach.year,
                "source": ach.source or "",
            }
            for ach in achievements
        ]

    def _get_community_data_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Get community statistics for statement of need."""
        community_data = self.db.query(CommunityData).filter(
            CommunityData.user_id == user_id
        ).all()

        # Group by data type for easier access
        grouped_data = {}
        for data in community_data:
            data_type = data.data_type.value if data.data_type else "other"
            if data_type not in grouped_data:
                grouped_data[data_type] = []

            grouped_data[data_type].append({
                "indicator": data.indicator,
                "statistic": data.statistic,
                "comparison_value": data.comparison_value or "",
                "trend": data.trend or "",
                "source": data.source,
                "source_year": data.source_year,
                "geographic_area": data.geographic_area or "",
            })

        return grouped_data

    def _get_budget_context(self, application_id: str) -> Dict[str, Any]:
        """Get budget details for the application."""
        line_items = self.db.query(BudgetLineItem).filter(
            BudgetLineItem.application_id == application_id
        ).order_by(BudgetLineItem.category, BudgetLineItem.sort_order).all()

        budget_context = {
            "line_items": [],
            "by_category": {},
            "total_request": 0,
            "total_match": 0,
            "grand_total": 0,
        }

        for item in line_items:
            total = (item.unit_cost or 0) * (item.quantity or 1)
            category = item.category.value if item.category else "other"

            item_dict = {
                "category": category,
                "description": item.description,
                "unit_cost": item.unit_cost,
                "quantity": item.quantity,
                "total": total,
                "justification": item.justification or "",
                "is_matching": item.is_matching or False,
            }

            budget_context["line_items"].append(item_dict)

            if category not in budget_context["by_category"]:
                budget_context["by_category"][category] = []
            budget_context["by_category"][category].append(item_dict)

            if item.is_matching:
                budget_context["total_match"] += total
            else:
                budget_context["total_request"] += total

            budget_context["grand_total"] += total

        return budget_context

    def _get_program_context(self, program_id: str) -> Dict[str, Any]:
        """Get grant program details."""
        program = self.db.query(GrantProgram).filter(
            GrantProgram.id == program_id
        ).first()

        if not program:
            return {}

        return {
            "id": program.id,
            "name": program.name,
            "agency": program.agency or "",
            "category": program.category.value if program.category else "",
            "min_award": program.min_award,
            "max_award": program.max_award,
            "match_required": program.match_required,
            "description": program.description or "",
            "eligibility_summary": program.eligibility_summary or "",
            "required_fields": self._parse_json_field(program.required_fields),
            "deadline": program.deadline.isoformat() if program.deadline else None,
            "rolling_deadline": program.rolling_deadline or False,
            "program_url": program.program_url or "",
        }

    def _get_application_context(self, application_id: str) -> Dict[str, Any]:
        """Get existing application data."""
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()

        if not application:
            return {}

        return {
            "id": application.id,
            "status": application.status.value if application.status else "draft",
            "form_data": self._parse_json_field(application.form_data),
            "completeness_score": application.completeness_score or 0,
        }

    def _build_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build a summary for quick reference in prompts."""
        org = context.get("organization", {})
        program = context.get("program", {})
        prior_grants = context.get("prior_grants", [])
        achievements = context.get("achievements", [])
        community_data = context.get("community_data", {})
        budget = context.get("budget", {})

        # Count awarded grants and total funding received
        awarded_grants = [g for g in prior_grants if g.get("status") == "awarded"]
        total_prior_funding = sum(g.get("amount", 0) or 0 for g in awarded_grants)

        # Count community data points
        total_data_points = sum(len(v) for v in community_data.values())

        return {
            "organization_name": org.get("name", ""),
            "organization_type": org.get("type", ""),
            "location": org.get("location", ""),
            "has_mission": bool(org.get("mission_statement")),
            "years_operating": org.get("years_in_operation") or org.get("founding_year"),
            "staff_size": org.get("staff_count") or org.get("employee_count"),
            "annual_budget": org.get("annual_budget") or org.get("annual_revenue"),
            "clients_served": org.get("clients_served_annually"),
            "num_prior_grants": len(awarded_grants),
            "total_prior_funding": total_prior_funding,
            "num_achievements": len(achievements),
            "num_community_data_points": total_data_points,
            "program_name": program.get("name", ""),
            "program_agency": program.get("agency", ""),
            "funding_range": f"${program.get('min_award', 0):,.0f} - ${program.get('max_award', 0):,.0f}",
            "match_required": program.get("match_required", 0),
            "budget_total": budget.get("grand_total", 0),
            "budget_request": budget.get("total_request", 0),
            "budget_match": budget.get("total_match", 0),
        }

    def _format_address(self, profile: UserProfile) -> str:
        """Format a full address string."""
        parts = []
        if profile.address:
            parts.append(profile.address)
        if profile.city:
            parts.append(profile.city)
        if profile.state:
            parts.append(profile.state)
        if profile.zip_code:
            parts.append(profile.zip_code)
        return ", ".join(parts)

    def _parse_json_field(self, value: Optional[str]) -> Any:
        """Safely parse a JSON field."""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
