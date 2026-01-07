"""
State Grant Portal Fetcher

Fetches grants from state-level grant portals:
- California Grants Portal (data.ca.gov) - FREE API
- Texas grants (future)
- New York grants (future)

All state portals use public open data APIs.
Cost: FREE
"""

import io
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx
from sqlalchemy.orm import Session

from app.models.database import GrantProgram, GrantCategory

logger = logging.getLogger(__name__)


# =============================================================================
# CATEGORY MAPPINGS
# =============================================================================

# California uses text categories - map to our enum
CA_CATEGORY_MAP = {
    "health": GrantCategory.HEALTHCARE,
    "education": GrantCategory.EDUCATION,
    "agriculture": GrantCategory.AGRICULTURE,
    "housing": GrantCategory.HOUSING,
    "science": GrantCategory.TECHNOLOGY,
    "technology": GrantCategory.TECHNOLOGY,
    "business": GrantCategory.SMALL_BUSINESS,
    "environment": GrantCategory.NONPROFIT,
    "community": GrantCategory.NONPROFIT,
    "arts": GrantCategory.NONPROFIT,
    "social": GrantCategory.NONPROFIT,
    "transportation": GrantCategory.NONPROFIT,
}

# Applicant type mappings to our standard org types
CA_APPLICANT_MAP = {
    "nonprofit": ["nonprofit", "501(c)(3)", "501c3"],
    "small_business": ["business", "small business"],
    "individual": ["individual"],
    "government": ["public agency", "city", "county", "state", "tribal"],
    "university": ["university", "college", "school", "education"],
}


# =============================================================================
# CALIFORNIA GRANTS FETCHER
# =============================================================================

class CaliforniaGrantsFetcher:
    """
    Fetch grants from California Grants Portal (grants.ca.gov).

    Data source: https://data.ca.gov/dataset/california-grants-portal
    API: CKAN datastore API (free, no auth required)
    Update frequency: Daily at 8:45 PM PT
    """

    BASE_URL = "https://data.ca.gov/api/3/action/datastore_search"
    RESOURCE_ID = "111c8c88-21f6-453c-ae2c-b4785a0624f5"
    CSV_URL = "https://data.ca.gov/dataset/e1b1c799-cdd4-4219-af6d-93b79747fffb/resource/111c8c88-21f6-453c-ae2c-b4785a0624f5/download/california-grants-portal-data.csv"

    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            "total_fetched": 0,
            "open_grants": 0,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    def fetch_and_sync(
        self,
        categories: Optional[List[str]] = None,
        min_award: Optional[float] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch California grants and sync to database.

        Args:
            categories: Filter by category keywords
            min_award: Minimum award amount
            max_results: Limit number of results (for testing)

        Returns:
            Dict with sync statistics
        """
        try:
            logger.info("Fetching California grants from data.ca.gov...")
            grants = self._fetch_grants()
            self.stats["total_fetched"] = len(grants)
            logger.info(f"Fetched {len(grants)} total grants from California")

            # Filter for open grants
            open_grants = self._filter_open(grants)
            self.stats["open_grants"] = len(open_grants)
            logger.info(f"Found {len(open_grants)} currently open grants")

            # Apply additional filters
            if categories:
                open_grants = [g for g in open_grants if self._matches_categories(g, categories)]
                logger.info(f"After category filter: {len(open_grants)}")

            if min_award:
                open_grants = [g for g in open_grants if self._meets_min_award(g, min_award)]
                logger.info(f"After min award filter: {len(open_grants)}")

            if max_results:
                open_grants = open_grants[:max_results]

            # Import to database
            logger.info("Importing to database...")
            for grant in open_grants:
                try:
                    self._upsert_grant(grant)
                except Exception as e:
                    self.stats["errors"].append(f"Error importing {grant.get('GrantID')}: {str(e)}")
                    self.stats["skipped"] += 1

            self.db.commit()
            logger.info(f"California sync complete: {self.stats['imported']} imported, {self.stats['updated']} updated")

            return self.stats

        except Exception as e:
            logger.error(f"California sync failed: {str(e)}")
            self.stats["errors"].append(f"Sync failed: {str(e)}")
            raise

    def _fetch_grants(self) -> List[Dict[str, Any]]:
        """Fetch all grants from CKAN API with pagination."""
        all_records = []
        offset = 0
        limit = 100

        with httpx.Client(timeout=60) as client:
            while True:
                url = f"{self.BASE_URL}?resource_id={self.RESOURCE_ID}&limit={limit}&offset={offset}"
                response = client.get(url)
                response.raise_for_status()

                data = response.json()
                if not data.get("success"):
                    raise Exception(f"API returned error: {data.get('error')}")

                records = data.get("result", {}).get("records", [])
                if not records:
                    break

                all_records.extend(records)
                offset += limit

                # Safety limit
                if offset > 5000:
                    logger.warning("Reached 5000 record safety limit")
                    break

        return all_records

    def _filter_open(self, grants: List[Dict]) -> List[Dict]:
        """Filter for currently open grant opportunities."""
        today = datetime.now()
        open_grants = []

        for grant in grants:
            status = (grant.get("Status") or "").lower()

            # Check status field
            if status not in ["open", "active", ""]:
                continue

            # Check deadline
            deadline_str = grant.get("ApplicationDeadline", "")
            if deadline_str:
                deadline = self._parse_date(deadline_str)
                if deadline and deadline < today:
                    continue

            open_grants.append(grant)

        return open_grants

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from California data."""
        if not date_str or date_str.lower() in ["ongoing", "continuous", "rolling", "n/a"]:
            return None

        formats = [
            "%B %d, %Y",        # January 15, 2025
            "%m/%d/%Y",         # 01/15/2025
            "%Y-%m-%d",         # 2025-01-15
            "%Y-%m-%dT%H:%M:%S", # ISO format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def _matches_categories(self, grant: Dict, categories: List[str]) -> bool:
        """Check if grant matches any specified categories."""
        grant_cats = (grant.get("Categories") or "").lower()
        return any(cat.lower() in grant_cats for cat in categories)

    def _meets_min_award(self, grant: Dict, min_award: float) -> bool:
        """Check if grant meets minimum award threshold."""
        amount_str = grant.get("EstAmounts", "") or grant.get("EstAvailFunds", "")
        amount = self._parse_amount(amount_str)
        return amount is not None and amount >= min_award

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse dollar amount from string."""
        if not amount_str:
            return None

        # Remove common characters
        cleaned = amount_str.replace("$", "").replace(",", "").strip()

        # Handle ranges like "$10,000 - $50,000"
        if "-" in cleaned:
            parts = cleaned.split("-")
            try:
                return float(parts[-1].strip())  # Take max of range
            except ValueError:
                pass

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _map_category(self, categories_str: str) -> GrantCategory:
        """Map California category strings to our GrantCategory enum."""
        if not categories_str:
            return GrantCategory.NONPROFIT

        cat_lower = categories_str.lower()
        for keyword, category in CA_CATEGORY_MAP.items():
            if keyword in cat_lower:
                return category

        return GrantCategory.NONPROFIT

    def _build_eligibility_summary(self, grant: Dict) -> str:
        """Build human-readable eligibility summary."""
        parts = []

        applicant_type = grant.get("ApplicantType", "")
        if applicant_type:
            parts.append(f"Eligible applicants: {applicant_type}")

        applicant_notes = grant.get("ApplicantTypeNotes", "")
        if applicant_notes:
            parts.append(applicant_notes[:500])

        geography = grant.get("Geography", "")
        if geography and geography.lower() != "statewide":
            parts.append(f"Geographic restriction: {geography}")

        return " ".join(parts) or "See grant details for eligibility requirements."

    def _upsert_grant(self, grant: Dict) -> None:
        """Insert or update a grant in the database."""
        grant_id = f"ca_state_{grant.get('GrantID', grant.get('_id', 'unknown'))}"

        existing = self.db.query(GrantProgram).filter(
            GrantProgram.id == grant_id
        ).first()

        # Parse amounts
        max_award = self._parse_amount(grant.get("EstAmounts", ""))
        if not max_award:
            max_award = self._parse_amount(grant.get("EstAvailFunds", ""))

        # Determine match requirement
        match_required = 0.0
        match_funds = (grant.get("MatchingFunds") or "").lower()
        if "yes" in match_funds or "required" in match_funds:
            match_required = 0.25  # Assume 25% match if required

        # Build data
        data = {
            "name": (grant.get("Title") or "California Grant")[:255],
            "agency": f"CA - {grant.get('AgencyDept', 'State Agency')}"[:100],
            "category": self._map_category(grant.get("Categories", "")),
            "min_award": None,  # CA doesn't always provide min
            "max_award": max_award,
            "match_required": match_required,
            "description": grant.get("Description") or grant.get("Purpose", ""),
            "eligibility_summary": self._build_eligibility_summary(grant),
            "deadline": self._parse_date(grant.get("ApplicationDeadline", "")),
            "rolling_deadline": grant.get("ApplicationDeadline", "").lower() in ["ongoing", "continuous", "rolling"],
            "program_url": grant.get("GrantURL") or grant.get("AgencyURL", ""),
            "application_url": grant.get("GrantURL", ""),
            "is_active": True,
        }

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            self.stats["updated"] += 1
        else:
            program = GrantProgram(id=grant_id, **data)
            self.db.add(program)
            self.stats["imported"] += 1

    def mark_expired_inactive(self) -> int:
        """Mark California grants with past deadlines as inactive."""
        today = datetime.now()
        count = self.db.query(GrantProgram).filter(
            GrantProgram.id.like("ca_state_%"),
            GrantProgram.deadline < today,
            GrantProgram.rolling_deadline == False,
            GrantProgram.is_active == True
        ).update({"is_active": False})
        self.db.commit()
        return count


# =============================================================================
# TEXAS GRANTS FETCHER (PLACEHOLDER)
# =============================================================================

class TexasGrantsFetcher:
    """
    Fetch grants from Texas grant portals.

    Texas doesn't have a single unified portal like California.
    Key sources:
    - Texas Health and Human Services (HHSC)
    - Texas Workforce Commission
    - Texas Department of Agriculture
    - Texas Education Agency

    Implementation pending - requires scraping multiple sources.
    """

    def __init__(self, db: Session):
        self.db = db
        self.stats = {"status": "not_implemented", "note": "Texas grants require multiple source integration"}

    def fetch_and_sync(self, **kwargs) -> Dict[str, Any]:
        """Placeholder - Texas grants fetcher not yet implemented."""
        logger.warning("Texas grants fetcher not yet implemented")
        return self.stats


# =============================================================================
# NEW YORK GRANTS FETCHER (PLACEHOLDER)
# =============================================================================

class NewYorkGrantsFetcher:
    """
    Fetch grants from New York State grant portal.

    NY has a grants gateway: https://grantsmanagement.ny.gov/
    But API access requires registration.

    Implementation pending.
    """

    def __init__(self, db: Session):
        self.db = db
        self.stats = {"status": "not_implemented", "note": "NY grants gateway requires registration"}

    def fetch_and_sync(self, **kwargs) -> Dict[str, Any]:
        """Placeholder - New York grants fetcher not yet implemented."""
        logger.warning("New York grants fetcher not yet implemented")
        return self.stats


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_california_fetcher(db: Session) -> CaliforniaGrantsFetcher:
    """Factory function to create California fetcher."""
    return CaliforniaGrantsFetcher(db)


def sync_california_grants(
    db: Session,
    categories: Optional[List[str]] = None,
    min_award: Optional[float] = None,
    max_results: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to sync California grants.

    Example:
        # Import all open California grants
        stats = sync_california_grants(db)

        # Import only health and education grants
        stats = sync_california_grants(db, categories=["health", "education"])
    """
    fetcher = create_california_fetcher(db)
    return fetcher.fetch_and_sync(
        categories=categories,
        min_award=min_award,
        max_results=max_results
    )


def sync_all_state_grants(
    db: Session,
    states: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Sync grants from all available state portals.

    Args:
        db: Database session
        states: List of state codes to sync (e.g., ["CA", "TX", "NY"])
                If None, syncs all available states.

    Returns:
        Dict mapping state code to sync statistics
    """
    results = {}

    available_fetchers = {
        "CA": CaliforniaGrantsFetcher,
        "TX": TexasGrantsFetcher,
        "NY": NewYorkGrantsFetcher,
    }

    states_to_sync = states or list(available_fetchers.keys())

    for state in states_to_sync:
        if state.upper() in available_fetchers:
            fetcher_class = available_fetchers[state.upper()]
            fetcher = fetcher_class(db)
            try:
                results[state.upper()] = fetcher.fetch_and_sync()
            except Exception as e:
                results[state.upper()] = {"error": str(e)}
        else:
            results[state.upper()] = {"error": f"No fetcher available for {state}"}

    return results
