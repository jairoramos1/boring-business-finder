#!/usr/bin/env python3
"""
Google Maps Scraper for Boring Business Finder

Scrapes business data from Google Maps using SerpAPI.
Includes demo mode for testing without API keys.
"""
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import config, Business, Review, SearchQuery, DATA_DIR

console = Console()


class GoogleMapsScraper:
    """Scrapes business data from Google Maps"""
    
    SERPAPI_BASE_URL = "https://serpapi.com/search"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.serpapi_key
        self.session = requests.Session()
        self.results_cache: Dict[str, List[Business]] = {}
    
    def search(
        self, 
        query: str, 
        location: str,
        max_results: int = 20
    ) -> List[Business]:
        """
        Search Google Maps for businesses
        
        Args:
            query: Business type to search (e.g., "garage organizers")
            location: City/area (e.g., "Charlotte, NC")
            max_results: Maximum number of results to return
            
        Returns:
            List of Business objects
        """
        search_query = SearchQuery(query=query, location=location)
        cache_key = f"{query}:{location}"
        
        if cache_key in self.results_cache:
            console.print(f"[dim]Using cached results for {cache_key}[/dim]")
            return self.results_cache[cache_key]
        
        if not self.api_key:
            console.print("[yellow]No API key - using demo data[/yellow]")
            return self._get_demo_data(query, location)
        
        console.print(f"[blue]Searching Google Maps for:[/blue] {search_query.search_string}")
        
        businesses = []
        start = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Scraping {query}...", total=None)
            
            while len(businesses) < max_results:
                params = {
                    "engine": "google_maps",
                    "q": search_query.search_string,
                    "type": "search",
                    "api_key": self.api_key,
                    "start": start,
                }
                
                try:
                    response = self.session.get(self.SERPAPI_BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                except requests.RequestException as e:
                    console.print(f"[red]API error: {e}[/red]")
                    break
                
                local_results = data.get("local_results", [])
                if not local_results:
                    break
                
                for result in local_results:
                    business = self._parse_result(result, location)
                    if business:
                        businesses.append(business)
                        progress.update(task, description=f"Found {len(businesses)} businesses...")
                
                # Check for more pages
                if len(local_results) < 20:
                    break
                    
                start += 20
                time.sleep(config.delay_between_requests)
        
        # Cache results
        self.results_cache[cache_key] = businesses[:max_results]
        
        console.print(f"[green]✓ Found {len(businesses)} businesses[/green]")
        return businesses[:max_results]
    
    def _parse_result(self, result: Dict[str, Any], location: str) -> Optional[Business]:
        """Parse a single search result into a Business object"""
        try:
            # Extract location parts
            address = result.get("address", "")
            city, state = self._parse_location(address, location)
            
            # Extract GPS coordinates
            gps = result.get("gps_coordinates", {})
            
            business = Business(
                name=result.get("title", "Unknown"),
                place_id=result.get("place_id", hashlib.md5(result.get("title", "").encode()).hexdigest()),
                category=result.get("type", "Unknown"),
                address=address,
                city=city,
                state=state,
                latitude=gps.get("latitude"),
                longitude=gps.get("longitude"),
                phone=result.get("phone"),
                website=result.get("website"),
                rating=result.get("rating"),
                review_count=result.get("reviews", 0),
            )
            
            return business
            
        except Exception as e:
            console.print(f"[dim]Skipping result: {e}[/dim]")
            return None
    
    def _parse_location(self, address: str, default_location: str) -> tuple:
        """Extract city and state from address"""
        parts = default_location.split(",")
        default_city = parts[0].strip() if parts else "Unknown"
        default_state = parts[1].strip() if len(parts) > 1 else "Unknown"
        
        # Try to parse from address
        addr_parts = address.split(",")
        if len(addr_parts) >= 2:
            city = addr_parts[-2].strip()
            state_zip = addr_parts[-1].strip().split()
            state = state_zip[0] if state_zip else default_state
            return city, state
        
        return default_city, default_state
    
    def get_reviews(self, place_id: str, max_reviews: int = 20) -> List[Review]:
        """Fetch reviews for a specific business"""
        if not self.api_key:
            return self._get_demo_reviews()
        
        params = {
            "engine": "google_maps_reviews",
            "place_id": place_id,
            "api_key": self.api_key,
        }
        
        try:
            response = self.session.get(self.SERPAPI_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            console.print(f"[red]Reviews API error: {e}[/red]")
            return []
        
        reviews = []
        for review_data in data.get("reviews", [])[:max_reviews]:
            review = Review(
                rating=review_data.get("rating", 3),
                text=review_data.get("snippet", ""),
                author=review_data.get("user", {}).get("name"),
            )
            reviews.append(review)
        
        return reviews
    
    def _get_demo_data(self, query: str, location: str) -> List[Business]:
        """Generate demo data for testing without API"""
        demo_businesses = [
            Business(
                name=f"Pro {query.title()} Services",
                place_id="demo_1",
                category=query,
                address="123 Main St",
                city=location.split(",")[0],
                state=location.split(",")[1].strip() if "," in location else "NC",
                phone="(555) 123-4567",
                website="https://example.com",
                rating=4.2,
                review_count=47,
                reviews=self._get_demo_reviews()
            ),
            Business(
                name=f"Budget {query.title()} Co",
                place_id="demo_2", 
                category=query,
                address="456 Oak Ave",
                city=location.split(",")[0],
                state=location.split(",")[1].strip() if "," in location else "NC",
                phone="(555) 234-5678",
                rating=3.1,
                review_count=23,
                reviews=self._get_demo_reviews(negative=True)
            ),
            Business(
                name=f"Elite {query.title()}",
                place_id="demo_3",
                category=query,
                address="789 Pine Rd",
                city=location.split(",")[0],
                state=location.split(",")[1].strip() if "," in location else "NC",
                phone="(555) 345-6789",
                website="https://elite-example.com",
                rating=4.8,
                review_count=156,
                reviews=self._get_demo_reviews()
            ),
            Business(
                name=f"Local {query.title()} Experts",
                place_id="demo_4",
                category=query,
                address="321 Elm St",
                city=location.split(",")[0],
                state=location.split(",")[1].strip() if "," in location else "NC",
                rating=2.9,
                review_count=12,
                reviews=self._get_demo_reviews(negative=True)
            ),
            Business(
                name=f"Family {query.title()} Service",
                place_id="demo_5",
                category=query,
                address="654 Maple Dr",
                city=location.split(",")[0],
                state=location.split(",")[1].strip() if "," in location else "NC",
                phone="(555) 456-7890",
                rating=4.5,
                review_count=89,
                reviews=self._get_demo_reviews()
            ),
        ]
        return demo_businesses
    
    def _get_demo_reviews(self, negative: bool = False) -> List[Review]:
        """Generate demo reviews"""
        if negative:
            return [
                Review(rating=1, text="Terrible service! They never showed up on time and the work was sloppy."),
                Review(rating=2, text="Overpriced and unprofessional. Would not recommend."),
                Review(rating=2, text="Communication was awful. Had to call multiple times to get updates."),
                Review(rating=3, text="Average work, but too expensive for what you get."),
                Review(rating=1, text="They damaged my property and refused to take responsibility."),
            ]
        return [
            Review(rating=5, text="Excellent service! Professional and on time."),
            Review(rating=4, text="Good work, fair prices. Would use again."),
            Review(rating=5, text="Best in the area. Highly recommend!"),
            Review(rating=4, text="Quality work, though scheduling took a while."),
            Review(rating=5, text="Transformed my space. Very happy with the results."),
        ]
    
    def save_results(self, businesses: List[Business], filename: Optional[str] = None) -> Path:
        """Save scraped results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scrape_{timestamp}.json"
        
        filepath = DATA_DIR / filename
        
        # Convert to serializable format
        data = {
            "scraped_at": datetime.now().isoformat(),
            "count": len(businesses),
            "businesses": [asdict(b) for b in businesses]
        }
        
        # Handle datetime serialization
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=serialize)
        
        console.print(f"[green]✓ Saved {len(businesses)} businesses to {filepath}[/green]")
        return filepath
    
    def display_results(self, businesses: List[Business]):
        """Display results in a formatted table"""
        table = Table(title="Scraped Businesses")
        
        table.add_column("Name", style="cyan")
        table.add_column("Rating", justify="center")
        table.add_column("Reviews", justify="right")
        table.add_column("Website", style="dim")
        table.add_column("Phone")
        
        for biz in businesses[:20]:  # Show first 20
            rating_color = "green" if biz.rating and biz.rating >= 4 else "yellow" if biz.rating and biz.rating >= 3 else "red"
            table.add_row(
                biz.name[:40],
                f"[{rating_color}]{biz.rating or 'N/A'}[/{rating_color}]",
                str(biz.review_count),
                "✓" if biz.website else "✗",
                biz.phone or "N/A"
            )
        
        console.print(table)
        
        if len(businesses) > 20:
            console.print(f"[dim]... and {len(businesses) - 20} more[/dim]")


def main():
    """CLI interface for the scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape Google Maps for boring businesses")
    parser.add_argument("--query", "-q", required=True, help="Business type to search")
    parser.add_argument("--location", "-l", required=True, help="City/area to search")
    parser.add_argument("--max", "-m", type=int, default=20, help="Max results")
    parser.add_argument("--save", "-s", action="store_true", help="Save results to file")
    parser.add_argument("--output", "-o", help="Output filename")
    
    args = parser.parse_args()
    
    scraper = GoogleMapsScraper()
    businesses = scraper.search(args.query, args.location, args.max)
    
    scraper.display_results(businesses)
    
    if args.save:
        scraper.save_results(businesses, args.output)


if __name__ == "__main__":
    main()
