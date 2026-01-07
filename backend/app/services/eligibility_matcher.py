"""
Smart Grant Eligibility Matching Service

Scores how well a user's profile matches each grant's eligibility requirements.
Returns a 0-100 match score based on:
- Organization type alignment
- Geographic eligibility
- Award size fit
- Category relevance
"""

import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.database import (
    GrantProgram,
    UserProfile,
    OrganizationProfile,
    GrantCategory
)


# Organization type mappings to Grants.gov eligibility codes
ORG_TYPE_ELIGIBILITY = {
    "nonprofit": ["12", "13"],  # 501(c)(3) and other nonprofits
    "nonprofit_501c3": ["12"],  # 501(c)(3) only
    "small_business": ["23"],
    "for_profit": ["22", "23"],  # For-profit and small business
    "individual": ["21"],
    "state_government": ["00"],
    "county_government": ["01"],
    "city_government": ["02"],
    "tribal_government": ["07", "11"],
    "university_public": ["06"],
    "university_private": ["20"],
    "school_district": ["05"],
    "housing_authority": ["08"],
}

# Keywords that indicate specific eligibility requirements
ELIGIBILITY_KEYWORDS = {
    "nonprofit": ["nonprofit", "501(c)(3)", "501c3", "non-profit", "tax-exempt"],
    "small_business": ["small business", "small businesses", "sbir", "sttr"],
    "individual": ["individual", "individuals", "person", "researcher"],
    "university": ["university", "universities", "higher education", "academic"],
    "government": ["state government", "local government", "tribal", "municipality"],
    "unrestricted": ["unrestricted", "any type", "all types", "open to any"],
}

# State abbreviations for geographic matching
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP"
}


class EligibilityMatcher:
    """
    Calculates match scores between user profiles and grant programs.

    Scoring breakdown:
    - Organization type match: 40 points
    - Award size fit: 25 points
    - Category relevance: 20 points
    - Geographic eligibility: 15 points
    """

    def __init__(self, db: Session):
        self.db = db

    def get_user_match_score(
        self,
        user_profile: UserProfile,
        org_profile: Optional[OrganizationProfile],
        grant: GrantProgram
    ) -> Dict:
        """
        Calculate match score for a single grant.

        Returns:
            Dict with score, breakdown, and eligibility status
        """
        breakdown = {
            "org_type": 0,
            "award_size": 0,
            "category": 0,
            "geographic": 0,
        }
        notes = []

        # 1. Organization Type Match (40 points)
        org_score, org_note = self._score_org_type(user_profile, grant)
        breakdown["org_type"] = org_score
        if org_note:
            notes.append(org_note)

        # 2. Award Size Fit (25 points)
        award_score, award_note = self._score_award_size(org_profile, grant)
        breakdown["award_size"] = award_score
        if award_note:
            notes.append(award_note)

        # 3. Category Relevance (20 points)
        cat_score, cat_note = self._score_category(user_profile, org_profile, grant)
        breakdown["category"] = cat_score
        if cat_note:
            notes.append(cat_note)

        # 4. Geographic Eligibility (15 points)
        geo_score, geo_note = self._score_geographic(user_profile, grant)
        breakdown["geographic"] = geo_score
        if geo_note:
            notes.append(geo_note)

        total_score = sum(breakdown.values())

        # Determine eligibility status
        if breakdown["org_type"] == 0 and grant.eligibility_summary:
            status = "likely_ineligible"
        elif total_score >= 70:
            status = "strong_match"
        elif total_score >= 50:
            status = "good_match"
        elif total_score >= 30:
            status = "possible_match"
        else:
            status = "weak_match"

        return {
            "score": total_score,
            "status": status,
            "breakdown": breakdown,
            "notes": notes,
        }

    def _score_org_type(
        self,
        profile: UserProfile,
        grant: GrantProgram
    ) -> Tuple[int, Optional[str]]:
        """Score organization type alignment (0-40 points)."""
        if not profile.organization_type:
            return 20, "Set your organization type to improve matching"

        eligibility_text = (grant.eligibility_summary or "").lower()
        org_type = profile.organization_type.lower().replace(" ", "_")

        # Check for unrestricted eligibility
        for keyword in ELIGIBILITY_KEYWORDS["unrestricted"]:
            if keyword in eligibility_text:
                return 40, "Open to all organization types"

        # Check if org type matches eligibility keywords
        if org_type in ELIGIBILITY_KEYWORDS:
            keywords = ELIGIBILITY_KEYWORDS[org_type]
            for keyword in keywords:
                if keyword in eligibility_text:
                    return 40, f"Eligible for {profile.organization_type}"

        # Check for explicit exclusion
        if "nonprofit" in org_type and "for-profit" in eligibility_text:
            if "nonprofit" not in eligibility_text:
                return 0, "Grant appears to be for-profit only"

        if "small_business" in org_type or "for_profit" in org_type:
            if "nonprofit" in eligibility_text and "for-profit" not in eligibility_text:
                return 0, "Grant appears to be nonprofit only"

        # Default - partial match if no explicit criteria
        return 25, "Verify eligibility requirements"

    def _score_award_size(
        self,
        org_profile: Optional[OrganizationProfile],
        grant: GrantProgram
    ) -> Tuple[int, Optional[str]]:
        """Score award size fit based on org budget (0-25 points)."""
        if not org_profile or not org_profile.annual_budget:
            return 15, "Add budget info to improve matching"

        budget = org_profile.annual_budget
        max_award = grant.max_award or 0
        min_award = grant.min_award or 0

        if max_award == 0:
            return 15, None  # No award info

        # Ideal: award is 10-50% of annual budget
        ideal_min = budget * 0.1
        ideal_max = budget * 0.5

        if min_award <= ideal_max and max_award >= ideal_min:
            return 25, f"Award range fits your budget"

        # Award too large for org capacity
        if min_award > budget:
            return 5, f"Award may exceed organizational capacity"

        # Award very small relative to budget
        if max_award < budget * 0.01:
            return 15, "Award is small relative to your budget"

        return 20, None

    def _score_category(
        self,
        user_profile: UserProfile,
        org_profile: Optional[OrganizationProfile],
        grant: GrantProgram
    ) -> Tuple[int, Optional[str]]:
        """Score category relevance (0-20 points)."""
        if not grant.category:
            return 10, None

        # Check mission statement for category keywords
        mission = ""
        if org_profile and org_profile.mission_statement:
            mission = org_profile.mission_statement.lower()

        category_keywords = {
            GrantCategory.HEALTHCARE: ["health", "medical", "clinic", "patient", "disease", "wellness"],
            GrantCategory.EDUCATION: ["education", "school", "student", "learning", "teach", "academic"],
            GrantCategory.TECHNOLOGY: ["technology", "research", "science", "innovation", "data", "computing"],
            GrantCategory.AGRICULTURE: ["agriculture", "farm", "food", "rural", "crop", "livestock"],
            GrantCategory.HOUSING: ["housing", "shelter", "homeless", "affordable", "rent"],
            GrantCategory.SMALL_BUSINESS: ["business", "entrepreneur", "startup", "commerce"],
            GrantCategory.NONPROFIT: ["community", "social", "service", "advocacy", "civic"],
        }

        if grant.category in category_keywords:
            keywords = category_keywords[grant.category]
            matches = sum(1 for kw in keywords if kw in mission)
            if matches >= 3:
                return 20, f"Strong alignment with your mission"
            elif matches >= 1:
                return 15, f"Aligns with your work"

        return 10, None

    def _score_geographic(
        self,
        profile: UserProfile,
        grant: GrantProgram
    ) -> Tuple[int, Optional[str]]:
        """Score geographic eligibility (0-15 points)."""
        if not profile.state:
            return 10, "Add location to verify geographic eligibility"

        # Check grant description/eligibility for state restrictions
        eligibility_text = (grant.eligibility_summary or "").lower()
        description = (grant.description or "").lower()
        combined = eligibility_text + " " + description

        # Check for national programs
        if "nationwide" in combined or "national" in combined:
            return 15, "Available nationwide"

        # Check for state-specific restrictions
        user_state = profile.state.upper()
        state_pattern = r'\b(' + '|'.join(US_STATES) + r')\b'
        mentioned_states = re.findall(state_pattern, combined.upper())

        if mentioned_states:
            if user_state in mentioned_states:
                return 15, f"Available in {user_state}"
            else:
                return 0, f"May be restricted to: {', '.join(set(mentioned_states))}"

        # Default - assume nationally available
        return 12, None

    def get_matched_grants(
        self,
        user_id: str,
        min_score: int = 30,
        category: Optional[GrantCategory] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get grants ranked by match score for a user.

        Args:
            user_id: The user's ID
            min_score: Minimum match score (0-100)
            category: Optional category filter
            limit: Max results to return

        Returns:
            List of grants with match scores, sorted by score descending
        """
        # Get user profiles
        user_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        org_profile = self.db.query(OrganizationProfile).filter(
            OrganizationProfile.user_id == user_id
        ).first()

        # Query grants
        query = self.db.query(GrantProgram).filter(
            GrantProgram.is_active == True
        )

        if category:
            query = query.filter(GrantProgram.category == category)

        grants = query.all()

        # Score each grant
        results = []
        for grant in grants:
            if user_profile:
                match_data = self.get_user_match_score(user_profile, org_profile, grant)
            else:
                # No profile - return neutral scores
                match_data = {
                    "score": 50,
                    "status": "create_profile",
                    "breakdown": {"org_type": 0, "award_size": 0, "category": 0, "geographic": 0},
                    "notes": ["Complete your profile for personalized matching"],
                }

            if match_data["score"] >= min_score:
                results.append({
                    "grant": grant,
                    "match": match_data,
                })

        # Sort by score descending
        results.sort(key=lambda x: x["match"]["score"], reverse=True)

        return results[:limit]


def create_eligibility_matcher(db: Session) -> EligibilityMatcher:
    """Factory function to create matcher instance."""
    return EligibilityMatcher(db)
