"""In-memory storage for leads."""

from typing import Optional
from app.models import Lead

# In-memory storage
_leads_db: dict[int, Lead] = {}
_next_lead_id = 1


def create_lead(name: str, company: str, role: str, phone: str, notes: Optional[str] = None) -> Lead:
    """Create a new lead."""
    global _next_lead_id
    
    lead = Lead(
        id=_next_lead_id,
        name=name,
        company=company,
        role=role,
        phone=phone,
        notes=notes
    )
    
    _leads_db[_next_lead_id] = lead
    _next_lead_id += 1
    
    return lead


def get_lead_by_id(lead_id: int) -> Optional[Lead]:
    """Get a lead by ID."""
    return _leads_db.get(lead_id)


def list_leads() -> list[Lead]:
    """List all leads."""
    return list(_leads_db.values())


def _init_sample_leads():
    """Initialize some sample leads for testing."""
    if not _leads_db:
        create_lead(
            name="Roy Habari Tamir",
            company="Habari Tamir Agents Ltd",
            role="CEO",
            phone="[REDACTED]",
            notes="Warm lead from conference"
        )
        create_lead(
            name="Gal Miles",
            company="Sales Corp",
            role="VP Sales",
            phone="[REDACTED]",
            notes="Inbound inquiry"
        )


# Initialize sample leads
_init_sample_leads()
