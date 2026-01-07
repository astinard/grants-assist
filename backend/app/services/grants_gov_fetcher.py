"""
Grants.gov Federal Grant Fetcher

Fetches and imports federal grants from Grants.gov's free daily XML extract.
Data source: https://www.grants.gov/xml-extract
Cost: FREE
"""

import io
import logging
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.models.database import GrantProgram, GrantCategory

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS AND MAPPINGS
# =============================================================================

GRANTS_GOV_BASE_URL = "https://prod-grants-gov-chatbot.s3.amazonaws.com/extracts"
XML_NAMESPACE = {"g": "http://apply.grants.gov/system/OpportunityDetail-V1.0"}

# Map Grants.gov category codes to our GrantCategory enum
CATEGORY_MAP = {
    "AG": GrantCategory.AGRICULTURE,
    "ED": GrantCategory.EDUCATION,
    "HL": GrantCategory.HEALTHCARE,
    "HO": GrantCategory.HOUSING,
    "ST": GrantCategory.TECHNOLOGY,
    "BC": GrantCategory.SMALL_BUSINESS,
    "CD": GrantCategory.NONPROFIT,      # Community Development
    "ISS": GrantCategory.NONPROFIT,     # Income Security & Social Services
    "FN": GrantCategory.NONPROFIT,      # Food & Nutrition
    "ENV": GrantCategory.NONPROFIT,     # Environment
    "NR": GrantCategory.NONPROFIT,      # Natural Resources
    "T": GrantCategory.TECHNOLOGY,      # Transportation
    "EN": GrantCategory.TECHNOLOGY,     # Energy
    "O": GrantCategory.NONPROFIT,       # Other
}

# Map eligibility codes to human-readable text
ELIGIBILITY_CODES = {
    "00": "State governments",
    "01": "County governments",
    "02": "City or township governments",
    "04": "Special district governments",
    "05": "Independent school districts",
    "06": "Public and State controlled institutions of higher education",
    "07": "Native American tribal governments (Federally recognized)",
    "08": "Public housing authorities/Indian housing authorities",
    "11": "Native American tribal organizations (other than Federally recognized)",
    "12": "Nonprofits having a 501(c)(3) status with the IRS",
    "13": "Nonprofits that do not have a 501(c)(3) status",
    "20": "Private institutions of higher education",
    "21": "Individuals",
    "22": "For-profit organizations other than small businesses",
    "23": "Small businesses",
    "25": "Others (see text field for eligibility details)",
    "99": "Unrestricted (i.e., open to any type of entity)",
}


# =============================================================================
# GRANTS.GOV FETCHER SERVICE
# =============================================================================

class GrantsGovFetcher:
    """
    Fetch and parse federal grants from Grants.gov XML extract.

    This service:
    1. Downloads the daily XML extract from Grants.gov (FREE)
    2. Parses all opportunities
    3. Filters for currently open grants
    4. Maps to our GrantProgram model
    5. Upserts to database
    """

    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            "downloaded": False,
            "total_in_extract": 0,
            "open_opportunities": 0,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    def fetch_and_sync(
        self,
        date: Optional[str] = None,
        categories: Optional[List[str]] = None,
        min_award: Optional[float] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Download extract, parse, and sync to database.

        Args:
            date: Date string YYYYMMDD (defaults to today)
            categories: List of category codes to filter (e.g., ["AG", "ED"])
            min_award: Minimum award ceiling to include
            max_results: Maximum number of grants to import (for testing)

        Returns:
            Dict with sync statistics
        """
        try:
            # 1. Download the ZIP file
            logger.info("Downloading Grants.gov extract...")
            xml_content = self._download_extract(date)
            self.stats["downloaded"] = True

            # 2. Parse XML and extract opportunities
            logger.info("Parsing XML...")
            opportunities = self._parse_xml(xml_content)
            self.stats["total_in_extract"] = len(opportunities)
            logger.info(f"Found {len(opportunities)} total opportunities in extract")

            # 3. Filter for open opportunities
            logger.info("Filtering for open opportunities...")
            open_opps = self._filter_open(opportunities)
            self.stats["open_opportunities"] = len(open_opps)
            logger.info(f"Found {len(open_opps)} currently open opportunities")

            # 4. Apply additional filters
            if categories:
                open_opps = [o for o in open_opps if self._matches_category(o, categories)]
                logger.info(f"After category filter: {len(open_opps)} opportunities")

            if min_award:
                open_opps = [o for o in open_opps if self._meets_min_award(o, min_award)]
                logger.info(f"After min award filter: {len(open_opps)} opportunities")

            if max_results:
                open_opps = open_opps[:max_results]
                logger.info(f"Limited to {len(open_opps)} opportunities")

            # 5. Import to database
            logger.info("Importing to database...")
            for opp in open_opps:
                try:
                    self._upsert_opportunity(opp)
                except Exception as e:
                    self.stats["errors"].append(f"Error importing {opp.get('id')}: {str(e)}")
                    self.stats["skipped"] += 1

            # Commit all changes
            self.db.commit()
            logger.info(f"Sync complete: {self.stats['imported']} imported, {self.stats['updated']} updated")

            return self.stats

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            self.stats["errors"].append(f"Sync failed: {str(e)}")
            raise

    def _download_extract(self, date: Optional[str] = None) -> bytes:
        """Download and extract the XML from Grants.gov."""
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        url = f"{GRANTS_GOV_BASE_URL}/GrantsDBExtract{date}v2.zip"
        logger.info(f"Downloading from: {url}")

        with httpx.Client(timeout=120) as client:
            response = client.get(url)
            response.raise_for_status()

        # Extract XML from ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_filename = zf.namelist()[0]
            logger.info(f"Extracting: {xml_filename}")
            return zf.read(xml_filename)

    def _parse_xml(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse XML and extract opportunity data."""
        root = ET.fromstring(xml_content)
        opportunities = []

        for opp_elem in root.findall(".//g:OpportunitySynopsisDetail_1_0", XML_NAMESPACE):
            opp = self._parse_opportunity(opp_elem)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _parse_opportunity(self, elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single opportunity element into a dict."""
        def get_text(tag: str) -> Optional[str]:
            el = elem.find(f"g:{tag}", XML_NAMESPACE)
            return el.text if el is not None and el.text else None

        def get_all_text(tag: str) -> List[str]:
            return [el.text for el in elem.findall(f"g:{tag}", XML_NAMESPACE) if el.text]

        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%m%d%Y")
            except ValueError:
                return None

        def parse_float(val: Optional[str]) -> Optional[float]:
            if not val:
                return None
            try:
                return float(val)
            except ValueError:
                return None

        opp_id = get_text("OpportunityID")
        if not opp_id:
            return None

        # Get eligibility codes and decode them
        elig_codes = get_all_text("EligibleApplicants")
        elig_text = get_text("AdditionalInformationOnEligibility") or ""
        decoded_elig = self._decode_eligibility(elig_codes, elig_text)

        # Get categories
        categories = get_all_text("CategoryOfFundingActivity")

        return {
            "id": f"grants_gov_{opp_id}",
            "opportunity_id": opp_id,
            "name": get_text("OpportunityTitle"),
            "opportunity_number": get_text("OpportunityNumber"),
            "agency": get_text("AgencyName"),
            "agency_code": get_text("AgencyCode"),
            "categories": categories,
            "category_explanation": get_text("CategoryExplanation"),
            "cfda_numbers": get_text("CFDANumbers"),
            "eligibility_codes": elig_codes,
            "eligibility_summary": decoded_elig,
            "description": get_text("Description"),
            "post_date": parse_date(get_text("PostDate")),
            "close_date": parse_date(get_text("CloseDate")),
            "archive_date": parse_date(get_text("ArchiveDate")),
            "award_ceiling": parse_float(get_text("AwardCeiling")),
            "award_floor": parse_float(get_text("AwardFloor")),
            "total_funding": parse_float(get_text("EstimatedTotalProgramFunding")),
            "expected_awards": get_text("ExpectedNumberOfAwards"),
            "cost_sharing": get_text("CostSharingOrMatchingRequirement"),
            "program_url": get_text("AdditionalInformationURL"),
            "contact_email": get_text("GrantorContactEmail"),
            "contact_text": get_text("GrantorContactText"),
        }

    def _decode_eligibility(self, codes: List[str], additional_text: str) -> str:
        """Decode eligibility codes into human-readable text."""
        decoded = []

        for code in codes:
            if code in ELIGIBILITY_CODES:
                decoded.append(ELIGIBILITY_CODES[code])
            else:
                decoded.append(f"Code {code}")

        result = ""
        if decoded:
            result = "Eligible applicants: " + ", ".join(decoded) + "."

        if additional_text:
            # Clean up HTML entities
            additional_text = (additional_text
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replace("&apos;", "'")
                .replace("<br/>", " ")
                .replace("<br>", " ")
            )
            if result:
                result += " " + additional_text
            else:
                result = additional_text

        return result.strip()

    def _filter_open(self, opportunities: List[Dict]) -> List[Dict]:
        """Filter for currently open opportunities."""
        today = datetime.now()
        return [
            opp for opp in opportunities
            if opp.get("close_date") and opp["close_date"] > today
        ]

    def _matches_category(self, opp: Dict, categories: List[str]) -> bool:
        """Check if opportunity matches any of the specified categories."""
        opp_cats = opp.get("categories", [])
        return any(cat in opp_cats for cat in categories)

    def _meets_min_award(self, opp: Dict, min_award: float) -> bool:
        """Check if opportunity meets minimum award threshold."""
        ceiling = opp.get("award_ceiling")
        return ceiling is not None and ceiling >= min_award

    def _map_category(self, categories: List[str]) -> Optional[GrantCategory]:
        """Map Grants.gov categories to our GrantCategory enum."""
        for cat in categories:
            if cat in CATEGORY_MAP:
                return CATEGORY_MAP[cat]
        return GrantCategory.NONPROFIT  # Default

    def _upsert_opportunity(self, opp: Dict) -> None:
        """Insert or update an opportunity in the database."""
        existing = self.db.query(GrantProgram).filter(
            GrantProgram.id == opp["id"]
        ).first()

        # Map to GrantProgram fields
        data = {
            "name": opp["name"][:255] if opp["name"] else "Untitled Opportunity",
            "agency": opp["agency"][:100] if opp["agency"] else None,
            "category": self._map_category(opp.get("categories", [])),
            "min_award": opp.get("award_floor"),
            "max_award": opp.get("award_ceiling"),
            "match_required": 0.5 if opp.get("cost_sharing") == "Yes" else 0.0,
            "description": opp.get("description"),
            "eligibility_summary": opp.get("eligibility_summary"),
            "deadline": opp.get("close_date"),
            "rolling_deadline": False,
            "program_url": opp.get("program_url")[:500] if opp.get("program_url") else f"https://www.grants.gov/search-results-detail/{opp['opportunity_id']}",
            "application_url": f"https://www.grants.gov/search-results-detail/{opp['opportunity_id']}",
            "is_active": True,
        }

        if existing:
            # Update existing record
            for key, value in data.items():
                setattr(existing, key, value)
            self.stats["updated"] += 1
        else:
            # Create new record
            program = GrantProgram(id=opp["id"], **data)
            self.db.add(program)
            self.stats["imported"] += 1

    def mark_expired_inactive(self) -> int:
        """Mark grants with past deadlines as inactive."""
        today = datetime.now()
        count = self.db.query(GrantProgram).filter(
            GrantProgram.id.like("grants_gov_%"),
            GrantProgram.deadline < today,
            GrantProgram.is_active == True
        ).update({"is_active": False})
        self.db.commit()
        return count


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_grants_gov_fetcher(db: Session) -> GrantsGovFetcher:
    """Factory function to create a fetcher instance."""
    return GrantsGovFetcher(db)


def sync_grants_gov(
    db: Session,
    categories: Optional[List[str]] = None,
    min_award: Optional[float] = None,
    max_results: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to sync grants from Grants.gov.

    Example:
        # Import all open grants
        stats = sync_grants_gov(db)

        # Import only agriculture and education grants with min $50k award
        stats = sync_grants_gov(db, categories=["AG", "ED"], min_award=50000)
    """
    fetcher = create_grants_gov_fetcher(db)
    return fetcher.fetch_and_sync(
        categories=categories,
        min_award=min_award,
        max_results=max_results
    )
