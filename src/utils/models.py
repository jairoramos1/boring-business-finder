"""
Data models for business information
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class BusinessCategory(Enum):
    """Common boring business categories"""
    GARAGE_ORGANIZERS = "garage organizers"
    IRRIGATION = "irrigation systems"
    PRESSURE_WASHING = "pressure washing"
    JUNK_REMOVAL = "junk removal"
    MOBILE_MECHANIC = "mobile mechanic"
    POOL_SERVICE = "pool service"
    LAWN_CARE = "lawn care"
    GUTTER_CLEANING = "gutter cleaning"
    APPLIANCE_REPAIR = "appliance repair"
    LOCKSMITH = "locksmith"
    FENCE_INSTALLATION = "fence installation"
    TREE_SERVICE = "tree service"
    CARPET_CLEANING = "carpet cleaning"
    WINDOW_CLEANING = "window cleaning"
    PEST_CONTROL = "pest control"
    OTHER = "other"


@dataclass
class Review:
    """A single customer review"""
    rating: int  # 1-5 stars
    text: str
    date: Optional[datetime] = None
    author: Optional[str] = None
    
    @property
    def is_negative(self) -> bool:
        return self.rating <= 2
    
    @property
    def is_positive(self) -> bool:
        return self.rating >= 4


@dataclass
class Business:
    """A business listing from Google Maps"""
    
    # Core info
    name: str
    place_id: str
    category: str
    
    # Location
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Contact
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Reviews
    rating: Optional[float] = None
    review_count: int = 0
    reviews: List[Review] = field(default_factory=list)
    
    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    
    @property
    def has_reviews(self) -> bool:
        return self.review_count > 0
    
    @property
    def negative_reviews(self) -> List[Review]:
        return [r for r in self.reviews if r.is_negative]
    
    @property
    def negative_review_ratio(self) -> float:
        if not self.reviews:
            return 0.0
        return len(self.negative_reviews) / len(self.reviews)


@dataclass
class OpportunityScore:
    """Scoring for a business niche opportunity"""
    
    category: str
    location: str
    
    # Volume metrics
    total_businesses: int = 0
    total_reviews: int = 0
    avg_reviews_per_business: float = 0.0
    
    # Quality metrics
    avg_rating: float = 0.0
    low_rated_businesses: int = 0  # < 4 stars
    businesses_without_website: int = 0
    
    # Velocity (if we have date data)
    reviews_last_30_days: int = 0
    review_velocity: float = 0.0  # reviews per day
    
    # Pain points
    common_complaints: List[str] = field(default_factory=list)
    complaint_themes: List[str] = field(default_factory=list)
    
    # Final score
    opportunity_score: int = 0  # 0-100
    
    def calculate_score(self) -> int:
        """Calculate overall opportunity score"""
        score = 0
        
        # Market size (0-25 points)
        if self.total_reviews > 1000:
            score += 25
        elif self.total_reviews > 500:
            score += 20
        elif self.total_reviews > 100:
            score += 15
        elif self.total_reviews > 50:
            score += 10
        else:
            score += 5
        
        # Competition gap (0-25 points) - fewer businesses = more opportunity
        if self.total_businesses < 10:
            score += 25
        elif self.total_businesses < 20:
            score += 20
        elif self.total_businesses < 50:
            score += 15
        else:
            score += 5
        
        # Quality gap (0-25 points) - low ratings = opportunity
        if self.avg_rating < 3.5:
            score += 25
        elif self.avg_rating < 4.0:
            score += 20
        elif self.avg_rating < 4.3:
            score += 15
        else:
            score += 5
        
        # Digital gap (0-25 points) - no websites = opportunity
        website_gap_ratio = self.businesses_without_website / max(self.total_businesses, 1)
        if website_gap_ratio > 0.5:
            score += 25
        elif website_gap_ratio > 0.3:
            score += 20
        elif website_gap_ratio > 0.1:
            score += 15
        else:
            score += 5
        
        self.opportunity_score = score
        return score


@dataclass
class SearchQuery:
    """A search query for Google Maps"""
    query: str
    location: str
    radius_miles: int = 25
    
    @property
    def search_string(self) -> str:
        return f"{self.query} in {self.location}"
