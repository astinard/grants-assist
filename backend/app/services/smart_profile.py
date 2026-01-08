"""
Smart Profile Service

Auto-populates user profile from external data sources:
- ProPublica Nonprofit Explorer API (org info from name/EIN)
- Census Bureau ACS API (demographics from ZIP code)
- USDA Rural-Urban Continuum Codes (rural eligibility)

All APIs are FREE and require no authentication.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NonprofitInfo:
    """Information about a nonprofit from ProPublica."""
    ein: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    ntee_code: Optional[str] = None
    subsection_code: Optional[str] = None  # 501(c)(3) = "03"
    is_501c3: bool = False
    total_revenue: Optional[float] = None
    total_assets: Optional[float] = None
    tax_period: Optional[str] = None


@dataclass
class CommunityDemographics:
    """Demographics for a ZIP code from Census Bureau."""
    zip_code: str
    location_name: Optional[str] = None
    total_population: Optional[int] = None
    median_household_income: Optional[float] = None
    poverty_count: Optional[int] = None
    poverty_rate: Optional[float] = None
    # Comparison to national averages
    income_vs_national: Optional[float] = None  # Ratio (< 1 = below average)
    poverty_vs_national: Optional[float] = None  # Ratio (> 1 = above average)
    is_high_need: bool = False  # Poverty > 20% or income < 60% national


@dataclass
class RuralStatus:
    """Rural classification from USDA codes."""
    zip_code: str
    is_rural: bool = False
    rucc_code: Optional[int] = None  # Rural-Urban Continuum Code
    description: Optional[str] = None
    qualifies_usda: bool = False
    qualifies_hrsa: bool = False


@dataclass
class SmartProfileData:
    """Combined profile data from all sources."""
    nonprofit: Optional[NonprofitInfo] = None
    demographics: Optional[CommunityDemographics] = None
    rural_status: Optional[RuralStatus] = None
    confidence_score: float = 0.0  # 0-100
    data_sources_used: List[str] = None

    def __post_init__(self):
        if self.data_sources_used is None:
            self.data_sources_used = []


# =============================================================================
# NATIONAL AVERAGES (2022 ACS)
# =============================================================================

NATIONAL_MEDIAN_INCOME = 74580  # US median household income 2022
NATIONAL_POVERTY_RATE = 11.5    # US poverty rate 2022


# =============================================================================
# NTEE CODE MAPPINGS
# =============================================================================

NTEE_TO_SECTOR = {
    "A": "arts_culture",
    "B": "education",
    "C": "environment",
    "D": "animal_welfare",
    "E": "healthcare",
    "F": "mental_health",
    "G": "disease_disorders",
    "H": "medical_research",
    "I": "crime_legal",
    "J": "employment",
    "K": "food_agriculture",
    "L": "housing",
    "M": "public_safety",
    "N": "recreation",
    "O": "youth_development",
    "P": "human_services",
    "Q": "international",
    "R": "civil_rights",
    "S": "community_improvement",
    "T": "philanthropy",
    "U": "science_technology",
    "V": "social_science",
    "W": "public_policy",
    "X": "religion",
    "Y": "mutual_benefit",
    "Z": "unknown",
}


# =============================================================================
# RUCC CODES (Rural-Urban Continuum)
# =============================================================================

RUCC_DESCRIPTIONS = {
    1: "Metro - 1+ million population",
    2: "Metro - 250,000 to 1 million",
    3: "Metro - Less than 250,000",
    4: "Nonmetro - Urban 20,000+, adjacent to metro",
    5: "Nonmetro - Urban 20,000+, not adjacent",
    6: "Nonmetro - Urban 2,500-19,999, adjacent",
    7: "Nonmetro - Urban 2,500-19,999, not adjacent",
    8: "Nonmetro - Completely rural, adjacent to metro",
    9: "Nonmetro - Completely rural, not adjacent",
}

# ZIP codes mapped to RUCC (sample - in production would use full dataset)
# For now, we'll use a heuristic based on population
RURAL_RUCC_CODES = {4, 5, 6, 7, 8, 9}  # Codes 4-9 are generally "rural"
VERY_RURAL_CODES = {7, 8, 9}  # More restrictive rural definition


# =============================================================================
# PROPUBLICA NONPROFIT API
# =============================================================================

class ProPublicaClient:
    """Client for ProPublica Nonprofit Explorer API."""

    BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"

    def __init__(self):
        self.client = httpx.Client(timeout=30)

    def search_by_name(self, name: str, state: Optional[str] = None) -> List[NonprofitInfo]:
        """Search for nonprofits by name."""
        try:
            params = {"q": name}
            if state:
                params["state[id]"] = state.upper()

            url = f"{self.BASE_URL}/search.json"
            response = self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            organizations = data.get("organizations", [])

            results = []
            for org in organizations[:10]:  # Limit to top 10
                results.append(self._parse_org(org))

            return results

        except Exception as e:
            logger.error(f"ProPublica search failed: {e}")
            return []

    def get_by_ein(self, ein: str) -> Optional[NonprofitInfo]:
        """Get nonprofit details by EIN."""
        try:
            # Clean EIN - remove dashes
            clean_ein = ein.replace("-", "")

            url = f"{self.BASE_URL}/organizations/{clean_ein}.json"
            response = self.client.get(url)
            response.raise_for_status()

            data = response.json()
            org = data.get("organization", {})
            filings = data.get("filings_with_data", [])

            info = self._parse_org(org)

            # Get latest filing data
            if filings:
                latest = filings[0]
                info.total_revenue = latest.get("totrevenue")
                info.total_assets = latest.get("totassetsend")
                info.tax_period = latest.get("tax_prd_yr")

            return info

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(f"EIN {ein} not found in ProPublica")
            else:
                logger.error(f"ProPublica EIN lookup failed: {e}")
            return None
        except Exception as e:
            logger.error(f"ProPublica EIN lookup failed: {e}")
            return None

    def _parse_org(self, org: Dict) -> NonprofitInfo:
        """Parse organization data from ProPublica response."""
        subsection = str(org.get("subsection_code", ""))

        return NonprofitInfo(
            ein=str(org.get("ein", "")),
            name=org.get("name", ""),
            city=org.get("city"),
            state=org.get("state"),
            ntee_code=org.get("ntee_code"),
            subsection_code=subsection,
            is_501c3=(subsection == "3" or subsection == "03"),
            total_revenue=org.get("income_amount"),
            total_assets=org.get("asset_amount"),
        )

    def close(self):
        self.client.close()


# =============================================================================
# CENSUS BUREAU API
# =============================================================================

class CensusClient:
    """Client for Census Bureau ACS API."""

    BASE_URL = "https://api.census.gov/data/2022/acs/acs5"

    # ACS variable codes
    VARIABLES = {
        "NAME": "NAME",
        "B19013_001E": "median_income",      # Median household income
        "B17001_002E": "poverty_count",      # Population in poverty
        "B01003_001E": "total_population",   # Total population
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30)

    def get_demographics(self, zip_code: str) -> Optional[CommunityDemographics]:
        """Get demographics for a ZIP code."""
        try:
            # Clean ZIP code
            clean_zip = zip_code.strip()[:5]

            params = {
                "get": ",".join(self.VARIABLES.keys()),
                "for": f"zip code tabulation area:{clean_zip}"
            }

            response = self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()

            if len(data) < 2:
                return None

            headers = data[0]
            values = data[1]

            # Parse values
            result = {}
            for i, header in enumerate(headers):
                if header in self.VARIABLES:
                    try:
                        result[self.VARIABLES[header]] = values[i]
                    except (IndexError, ValueError):
                        pass

            # Calculate demographics
            population = int(result.get("total_population", 0)) if result.get("total_population") else None
            poverty_count = int(result.get("poverty_count", 0)) if result.get("poverty_count") else None
            median_income = float(result.get("median_income", 0)) if result.get("median_income") else None

            poverty_rate = None
            if population and poverty_count:
                poverty_rate = (poverty_count / population) * 100

            # Calculate comparisons to national averages
            income_vs_national = None
            poverty_vs_national = None
            is_high_need = False

            if median_income:
                income_vs_national = median_income / NATIONAL_MEDIAN_INCOME

            if poverty_rate:
                poverty_vs_national = poverty_rate / NATIONAL_POVERTY_RATE

            # High need: poverty > 20% OR income < 60% of national
            if poverty_rate and poverty_rate > 20:
                is_high_need = True
            if income_vs_national and income_vs_national < 0.6:
                is_high_need = True

            return CommunityDemographics(
                zip_code=clean_zip,
                location_name=result.get("NAME"),
                total_population=population,
                median_household_income=median_income,
                poverty_count=poverty_count,
                poverty_rate=poverty_rate,
                income_vs_national=income_vs_national,
                poverty_vs_national=poverty_vs_national,
                is_high_need=is_high_need,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Census API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Census lookup failed: {e}")
            return None

    def close(self):
        self.client.close()


# =============================================================================
# RURAL STATUS CHECKER
# =============================================================================

class RuralChecker:
    """Check rural status using heuristics and Census data."""

    def __init__(self, census_client: CensusClient):
        self.census = census_client

    def check_rural_status(self, zip_code: str, demographics: Optional[CommunityDemographics] = None) -> RuralStatus:
        """
        Determine rural status for a ZIP code.

        Uses population-based heuristics since full RUCC mapping
        would require a large lookup table.
        """
        if demographics is None:
            demographics = self.census.get_demographics(zip_code)

        if demographics is None:
            return RuralStatus(zip_code=zip_code)

        population = demographics.total_population or 0

        # Heuristic RUCC assignment based on population
        # In production, use actual FIPS-to-RUCC mapping
        if population >= 50000:
            rucc = 1  # Metro
        elif population >= 20000:
            rucc = 3  # Small metro
        elif population >= 10000:
            rucc = 4  # Nonmetro urban adjacent
        elif population >= 2500:
            rucc = 6  # Nonmetro small urban
        else:
            rucc = 8  # Completely rural

        is_rural = rucc in RURAL_RUCC_CODES

        return RuralStatus(
            zip_code=zip_code,
            is_rural=is_rural,
            rucc_code=rucc,
            description=RUCC_DESCRIPTIONS.get(rucc, "Unknown"),
            qualifies_usda=is_rural,  # USDA rural programs
            qualifies_hrsa=rucc in VERY_RURAL_CODES,  # HRSA often stricter
        )


# =============================================================================
# SMART PROFILE SERVICE
# =============================================================================

class SmartProfileService:
    """
    Main service for auto-populating user profiles.

    Usage:
        service = SmartProfileService()

        # Lookup by org name
        data = service.lookup_nonprofit("Rural Health Clinic of Kentucky")

        # Lookup by ZIP
        data = service.lookup_by_zip("40831")

        # Full profile enrichment
        data = service.enrich_profile(
            org_name="Rural Health Clinic",
            zip_code="40831",
            ein="12-3456789"
        )
    """

    def __init__(self):
        self.propublica = ProPublicaClient()
        self.census = CensusClient()
        self.rural_checker = RuralChecker(self.census)

    def lookup_nonprofit(self, name: str, state: Optional[str] = None) -> List[NonprofitInfo]:
        """Search for nonprofits by name."""
        return self.propublica.search_by_name(name, state)

    def lookup_by_ein(self, ein: str) -> Optional[NonprofitInfo]:
        """Get nonprofit details by EIN."""
        return self.propublica.get_by_ein(ein)

    def lookup_by_zip(self, zip_code: str) -> SmartProfileData:
        """Get demographics and rural status for a ZIP code."""
        demographics = self.census.get_demographics(zip_code)
        rural_status = self.rural_checker.check_rural_status(zip_code, demographics)

        data_sources = []
        confidence = 0.0

        if demographics:
            data_sources.append("census_acs_2022")
            confidence += 40

        if rural_status.rucc_code:
            data_sources.append("usda_rucc_estimate")
            confidence += 20

        return SmartProfileData(
            demographics=demographics,
            rural_status=rural_status,
            confidence_score=confidence,
            data_sources_used=data_sources,
        )

    def enrich_profile(
        self,
        org_name: Optional[str] = None,
        ein: Optional[str] = None,
        zip_code: Optional[str] = None,
        state: Optional[str] = None,
    ) -> SmartProfileData:
        """
        Enrich a profile using all available data sources.

        Args:
            org_name: Organization name to search
            ein: EIN for direct lookup
            zip_code: ZIP code for demographics
            state: State code for narrowing search

        Returns:
            SmartProfileData with all available information
        """
        result = SmartProfileData()
        confidence = 0.0

        # 1. Nonprofit lookup
        if ein:
            result.nonprofit = self.lookup_by_ein(ein)
            if result.nonprofit:
                result.data_sources_used.append("propublica_ein")
                confidence += 50
        elif org_name:
            matches = self.lookup_nonprofit(org_name, state)
            if matches:
                result.nonprofit = matches[0]  # Best match
                result.data_sources_used.append("propublica_search")
                confidence += 30  # Less confident than EIN lookup

        # 2. ZIP code lookup
        if zip_code:
            zip_data = self.lookup_by_zip(zip_code)
            result.demographics = zip_data.demographics
            result.rural_status = zip_data.rural_status
            result.data_sources_used.extend(zip_data.data_sources_used)
            confidence += zip_data.confidence_score

        # Normalize confidence to 0-100
        result.confidence_score = min(100, confidence)

        return result

    def get_sector_from_ntee(self, ntee_code: Optional[str]) -> Optional[str]:
        """Map NTEE code to sector."""
        if not ntee_code:
            return None
        return NTEE_TO_SECTOR.get(ntee_code[0].upper())

    def close(self):
        """Clean up HTTP clients."""
        self.propublica.close()
        self.census.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_smart_profile_service() -> SmartProfileService:
    """Factory function to create SmartProfileService."""
    return SmartProfileService()


def quick_nonprofit_lookup(name: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Quick nonprofit search returning dict format.

    Example:
        results = quick_nonprofit_lookup("Stanford University")
        # Returns list of dicts with EIN, name, is_501c3, etc.
    """
    service = create_smart_profile_service()
    try:
        nonprofits = service.lookup_nonprofit(name, state)
        return [
            {
                "ein": np.ein,
                "name": np.name,
                "city": np.city,
                "state": np.state,
                "is_501c3": np.is_501c3,
                "ntee_code": np.ntee_code,
                "total_revenue": np.total_revenue,
                "total_assets": np.total_assets,
            }
            for np in nonprofits
        ]
    finally:
        service.close()


def quick_zip_lookup(zip_code: str) -> Dict[str, Any]:
    """
    Quick ZIP code lookup returning dict format.

    Example:
        data = quick_zip_lookup("40831")
        # Returns dict with demographics and rural status
    """
    service = create_smart_profile_service()
    try:
        data = service.lookup_by_zip(zip_code)
        result = {
            "zip_code": zip_code,
            "confidence_score": data.confidence_score,
            "data_sources": data.data_sources_used,
        }

        if data.demographics:
            result["demographics"] = {
                "location_name": data.demographics.location_name,
                "population": data.demographics.total_population,
                "median_income": data.demographics.median_household_income,
                "poverty_rate": round(data.demographics.poverty_rate, 1) if data.demographics.poverty_rate else None,
                "is_high_need": data.demographics.is_high_need,
                "income_vs_national": round(data.demographics.income_vs_national, 2) if data.demographics.income_vs_national else None,
            }

        if data.rural_status:
            result["rural_status"] = {
                "is_rural": data.rural_status.is_rural,
                "rucc_code": data.rural_status.rucc_code,
                "description": data.rural_status.description,
                "qualifies_usda": data.rural_status.qualifies_usda,
                "qualifies_hrsa": data.rural_status.qualifies_hrsa,
            }

        return result
    finally:
        service.close()
