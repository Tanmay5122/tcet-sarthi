"""
SQLAlchemy ORM Model for Opportunities
Supports: internships, hackathons, grants, workshops, placements
Sources: TCET, Unstop, Internshala, government portals
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Index, func, UniqueConstraint
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, Field, validator
import hashlib

Base = declarative_base()


class OpportunityModel(Base):
    """
    SQLAlchemy ORM Model for storing opportunities from multiple sources.
    
    Features:
    - Automatic deduplication via MD5 hash
    - Expired opportunity tracking
    - Confidence scoring (0.0-1.0)
    - Semantic search support (embeddings in Phase 3)
    - Source tracking for audit
    """
    
    __tablename__ = "raw_opportunities"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Source Information
    source = Column(String(50), nullable=False, index=True)  # TCET, Unstop, Internshala, NSF, ProQuest
    source_id = Column(String(255), nullable=True, unique=False, index=True)  # External ID from source
    source_url = Column(String(500), nullable=False, unique=True)  # URL where we found it
    
    # Opportunity Type
    opportunity_type = Column(String(50), nullable=False, index=True)  # internship, hackathon, grant, workshop, placement
    category = Column(String(100), nullable=True, index=True)  # AI, ML, Web Dev, Data Science, etc.
    
    # Core Information
    title = Column(String(255), nullable=False, index=True)
    organization = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)  # Long description
    short_description = Column(String(500), nullable=True)  # 1-line summary
    
    # Key Details
    deadline = Column(DateTime, nullable=False, index=True)  # Application deadline
    start_date = Column(DateTime, nullable=True)  # When opportunity starts (for internships)
    duration = Column(String(100), nullable=True)  # "6 months", "3 months", etc.
    
    # Compensation
    salary_min = Column(Integer, nullable=True)  # Minimum salary/stipend (in rupees)
    salary_max = Column(Integer, nullable=True)  # Maximum salary/stipend
    salary_currency = Column(String(10), default="INR", nullable=False)
    is_paid = Column(Boolean, default=False)  # Whether it's paid or unpaid
    
    # Location & Eligibility
    location = Column(String(255), nullable=True, index=True)  # City/country
    is_remote = Column(Boolean, default=False)  # Remote option available
    
    # Requirements
    min_year = Column(Integer, nullable=True)  # Minimum year (1st, 2nd, 3rd, 4th year)
    max_year = Column(Integer, nullable=True)  # Maximum year
    required_skills = Column(Text, nullable=True)  # Comma-separated: Python, ML, Java, etc.
    required_cgpa = Column(Float, nullable=True)  # Minimum CGPA required
    
    # Additional Info
    perks = Column(Text, nullable=True)  # Benefits/perks (PPO, travel reimbursement, etc.)
    selection_process = Column(Text, nullable=True)  # Online test, interview, assessment
    application_url = Column(String(500), nullable=True)  # Direct application link
    
    # Deduplication & Quality
    source_hash = Column(String(32), unique=True, nullable=False, index=True)  # MD5 hash of (title + org + deadline)
    confidence_score = Column(Float, default=0.7, nullable=False)  # 0.0-1.0, how confident in data accuracy
    
    # Status Tracking
    is_expired = Column(Boolean, default=False, index=True)  # Mark as expired when deadline passes
    is_active = Column(Boolean, default=True, index=True)  # Admin can deactivate
    
    # Timestamps
    scraped_at = Column(DateTime, default=func.now(), nullable=False)  # When we scraped it
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Audit & Tracking
    scraper_version = Column(String(50), nullable=True)  # Which version of scraper found it
    data_quality_notes = Column(Text, nullable=True)  # Any issues during scraping
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_deadline_active', 'deadline', 'is_active'),
        Index('idx_source_type_active', 'source', 'opportunity_type', 'is_active'),
        Index('idx_org_active', 'organization', 'is_active'),
        Index('idx_location_active', 'location', 'is_active'),
        UniqueConstraint('source', 'source_id', name='uq_source_source_id'),
    )
    
    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title}', source='{self.source}', deadline={self.deadline})>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'source': self.source,
            'type': self.opportunity_type,
            'category': self.category,
            'title': self.title,
            'organization': self.organization,
            'description': self.description,
            'short_description': self.short_description,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'duration': self.duration,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_currency': self.salary_currency,
            'is_paid': self.is_paid,
            'location': self.location,
            'is_remote': self.is_remote,
            'min_year': self.min_year,
            'max_year': self.max_year,
            'required_skills': self.required_skills,
            'required_cgpa': self.required_cgpa,
            'perks': self.perks,
            'selection_process': self.selection_process,
            'application_url': self.application_url,
            'confidence_score': self.confidence_score,
            'is_expired': self.is_expired,
            'is_active': self.is_active,
            'source_url': self.source_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# PYDANTIC MODELS FOR VALIDATION (API + Scraper Input)
# ============================================================================

class OpportunityBase(BaseModel):
    """Base schema with all fields"""
    source: str
    source_id: Optional[str] = None
    source_url: str
    opportunity_type: str  # internship, hackathon, grant, etc.
    category: Optional[str] = None
    title: str
    organization: str
    description: str
    short_description: Optional[str] = None
    deadline: datetime
    start_date: Optional[datetime] = None
    duration: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "INR"
    is_paid: bool = False
    location: Optional[str] = None
    is_remote: bool = False
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    required_skills: Optional[str] = None
    required_cgpa: Optional[float] = None
    perks: Optional[str] = None
    selection_process: Optional[str] = None
    application_url: Optional[str] = None
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    is_expired: bool = False
    is_active: bool = True
    scraper_version: Optional[str] = None
    data_quality_notes: Optional[str] = None
    
    @validator('source')
    def validate_source(cls, v):
        """Ensure source is from allowed list"""
        allowed = {'TCET', 'Unstop', 'Internshala', 'NSF', 'ProQuest', 'Government'}
        if v not in allowed:
            raise ValueError(f'source must be one of {allowed}')
        return v
    
    @validator('opportunity_type')
    def validate_type(cls, v):
        """Ensure type is valid"""
        allowed = {'internship', 'hackathon', 'grant', 'workshop', 'placement', 'fellowship', 'scholarship'}
        if v.lower() not in allowed:
            raise ValueError(f'opportunity_type must be one of {allowed}')
        return v.lower()
    
    @validator('deadline')
    def validate_deadline(cls, v):
        """Ensure deadline is in the future"""
        if v < datetime.now():
            raise ValueError('deadline must be in the future')
        return v
    
    @validator('salary_min', 'salary_max', pre=True)
    def validate_salary(cls, v):
        """Ensure salary values are positive"""
        if v is not None and v < 0:
            raise ValueError('salary must be positive')
        return v
    
    class Config:
        from_attributes = True


class OpportunityCreate(OpportunityBase):
    """Schema for creating new opportunities (scraper input)"""
    pass


class OpportunityUpdate(BaseModel):
    """Schema for updating opportunities"""
    is_expired: Optional[bool] = None
    is_active: Optional[bool] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_quality_notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class OpportunityResponse(OpportunityBase):
    """Schema for API responses"""
    id: int
    source_hash: str
    created_at: datetime
    updated_at: datetime
    scraped_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_source_hash(title: str, organization: str, deadline: datetime) -> str:
    """
    Generate MD5 hash for deduplication.
    
    Args:
        title: Opportunity title
        organization: Organization name
        deadline: Application deadline
    
    Returns:
        32-character MD5 hash (lowercase)
    
    Example:
        >>> hash = generate_source_hash('Python Internship', 'Google', datetime(2026, 12, 31))
        >>> len(hash)
        32
    """
    # Normalize strings and create unique key
    clean_title = title.strip().lower()
    clean_org = organization.strip().lower()
    deadline_str = deadline.strftime('%Y-%m-%d')
    
    unique_string = f"{clean_title}|{clean_org}|{deadline_str}"
    hash_value = hashlib.md5(unique_string.encode()).hexdigest()
    
    return hash_value


if __name__ == "__main__":
    """Test the model"""
    print("✓ OpportunityModel imported successfully")
    print(f"✓ Table name: {OpportunityModel.__tablename__}")
    print(f"✓ Columns: {len(OpportunityModel.__table__.columns)}")
    
    # Test hash generation
    test_hash = generate_source_hash(
        "Python Internship",
        "Google",
        datetime(2026, 12, 31)
    )
    print(f"✓ Test hash: {test_hash}")
    print(f"✓ Hash length: {len(test_hash)}")