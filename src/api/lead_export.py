#!/usr/bin/env python3
"""
Lead Export System for Boring Business Finder

Exports business data in various formats for lead generation:
- CSV exports for outreach
- JSON API for integrations
- SQLite database for persistence
- Enrichment with contact details
"""
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import asdict

from rich.console import Console
from rich.table import Table
from rich.progress import track

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import config, Business, DATA_DIR, OUTPUT_DIR

console = Console()


class LeadDatabase:
    """SQLite database for storing and querying leads"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.database_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    place_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    phone TEXT,
                    website TEXT,
                    rating REAL,
                    review_count INTEGER,
                    latitude REAL,
                    longitude REAL,
                    scraped_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    place_id TEXT,
                    rating INTEGER,
                    text TEXT,
                    author TEXT,
                    review_date TIMESTAMP,
                    FOREIGN KEY (place_id) REFERENCES businesses(place_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    location TEXT,
                    result_count INTEGER,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        
        console.print(f"[dim]Database initialized: {self.db_path}[/dim]")
    
    def insert_businesses(self, businesses: List[Business]) -> int:
        """Insert or update businesses in database"""
        inserted = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for biz in businesses:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO businesses 
                        (place_id, name, category, address, city, state, zip_code,
                         phone, website, rating, review_count, latitude, longitude, 
                         scraped_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        biz.place_id, biz.name, biz.category, biz.address,
                        biz.city, biz.state, biz.zip_code, biz.phone, biz.website,
                        biz.rating, biz.review_count, biz.latitude, biz.longitude,
                        biz.scraped_at.isoformat() if biz.scraped_at else None
                    ))
                    
                    # Insert reviews
                    for review in biz.reviews:
                        conn.execute("""
                            INSERT INTO reviews (place_id, rating, text, author)
                            VALUES (?, ?, ?, ?)
                        """, (biz.place_id, review.rating, review.text, review.author))
                    
                    inserted += 1
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not insert {biz.name}: {e}[/yellow]")
            
            conn.commit()
        
        console.print(f"[green]✓ Inserted/updated {inserted} businesses[/green]")
        return inserted
    
    def search(
        self,
        category: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        has_website: Optional[bool] = None,
        has_phone: Optional[bool] = None,
        min_reviews: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search businesses with filters"""
        query = "SELECT * FROM businesses WHERE 1=1"
        params = []
        
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
        
        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")
        
        if state:
            query += " AND state = ?"
            params.append(state)
        
        if min_rating is not None:
            query += " AND rating >= ?"
            params.append(min_rating)
        
        if max_rating is not None:
            query += " AND rating <= ?"
            params.append(max_rating)
        
        if has_website is True:
            query += " AND website IS NOT NULL AND website != ''"
        elif has_website is False:
            query += " AND (website IS NULL OR website = '')"
        
        if has_phone is True:
            query += " AND phone IS NOT NULL AND phone != ''"
        elif has_phone is False:
            query += " AND (phone IS NULL OR phone = '')"
        
        if min_reviews is not None:
            query += " AND review_count >= ?"
            params.append(min_reviews)
        
        query += f" ORDER BY review_count DESC LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            stats["total_businesses"] = conn.execute(
                "SELECT COUNT(*) FROM businesses"
            ).fetchone()[0]
            
            stats["total_reviews"] = conn.execute(
                "SELECT COUNT(*) FROM reviews"
            ).fetchone()[0]
            
            stats["categories"] = conn.execute(
                "SELECT DISTINCT category FROM businesses"
            ).fetchall()
            stats["categories"] = [c[0] for c in stats["categories"] if c[0]]
            
            stats["cities"] = conn.execute(
                "SELECT city, COUNT(*) as count FROM businesses GROUP BY city ORDER BY count DESC LIMIT 10"
            ).fetchall()
            
            stats["avg_rating"] = conn.execute(
                "SELECT AVG(rating) FROM businesses WHERE rating IS NOT NULL"
            ).fetchone()[0]
        
        return stats


class LeadExporter:
    """Exports leads in various formats"""
    
    def __init__(self, db: Optional[LeadDatabase] = None):
        self.db = db or LeadDatabase()
    
    def export_csv(
        self,
        businesses: List[Dict[str, Any]],
        filename: Optional[str] = None,
        include_fields: Optional[List[str]] = None
    ) -> Path:
        """Export businesses to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{timestamp}.csv"
        
        filepath = OUTPUT_DIR / filename
        
        # Default fields
        default_fields = [
            "name", "category", "address", "city", "state",
            "phone", "website", "rating", "review_count"
        ]
        fields = include_fields or default_fields
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            
            for biz in businesses:
                writer.writerow(biz)
        
        console.print(f"[green]✓ Exported {len(businesses)} leads to {filepath}[/green]")
        return filepath
    
    def export_json(
        self,
        businesses: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """Export businesses to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{timestamp}.json"
        
        filepath = OUTPUT_DIR / filename
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "count": len(businesses),
            "leads": businesses
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        console.print(f"[green]✓ Exported {len(businesses)} leads to {filepath}[/green]")
        return filepath
    
    def export_outreach_list(
        self,
        businesses: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """Export optimized list for cold outreach"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outreach_{timestamp}.csv"
        
        filepath = OUTPUT_DIR / filename
        
        # Priority fields for outreach
        fields = [
            "name", "phone", "website", "city", "state",
            "rating", "review_count", "opportunity_notes"
        ]
        
        # Add opportunity notes based on data
        enriched = []
        for biz in businesses:
            notes = []
            
            if biz.get("rating") and biz["rating"] < 4.0:
                notes.append("Below avg rating - may want help")
            
            if not biz.get("website"):
                notes.append("No website - digital marketing opportunity")
            
            if biz.get("review_count", 0) < 20:
                notes.append("Low review count - reputation management")
            
            biz["opportunity_notes"] = "; ".join(notes) if notes else "Standard outreach"
            enriched.append(biz)
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(enriched)
        
        console.print(f"[green]✓ Exported {len(enriched)} outreach leads to {filepath}[/green]")
        return filepath
    
    def display_leads(self, businesses: List[Dict[str, Any]], limit: int = 20):
        """Display leads in a formatted table"""
        table = Table(title=f"Leads ({len(businesses)} total)")
        
        table.add_column("Name", style="cyan", max_width=30)
        table.add_column("City")
        table.add_column("Rating", justify="center")
        table.add_column("Reviews", justify="right")
        table.add_column("Phone")
        table.add_column("Website", style="dim")
        
        for biz in businesses[:limit]:
            rating = biz.get("rating")
            rating_str = f"{rating:.1f}" if rating else "N/A"
            rating_color = "green" if rating and rating >= 4 else "yellow" if rating and rating >= 3 else "red"
            
            table.add_row(
                biz.get("name", "Unknown")[:30],
                biz.get("city", ""),
                f"[{rating_color}]{rating_str}[/{rating_color}]",
                str(biz.get("review_count", 0)),
                biz.get("phone", "N/A") or "N/A",
                "✓" if biz.get("website") else "✗"
            )
        
        console.print(table)
        
        if len(businesses) > limit:
            console.print(f"[dim]... and {len(businesses) - limit} more[/dim]")


def load_businesses_from_json(filepath: Path) -> List[Dict[str, Any]]:
    """Load businesses from scrape JSON file"""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("businesses", [])


def main():
    """CLI for lead export system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export and manage leads")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import scraped data to database")
    import_parser.add_argument("--input", "-i", help="Input JSON file")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export leads")
    export_parser.add_argument("--format", "-f", choices=["csv", "json", "outreach"], default="csv")
    export_parser.add_argument("--category", "-c", help="Filter by category")
    export_parser.add_argument("--city", help="Filter by city")
    export_parser.add_argument("--min-rating", type=float, help="Minimum rating")
    export_parser.add_argument("--max-rating", type=float, help="Maximum rating")
    export_parser.add_argument("--no-website", action="store_true", help="Only businesses without website")
    export_parser.add_argument("--limit", type=int, default=100, help="Max results")
    export_parser.add_argument("--output", "-o", help="Output filename")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search leads")
    search_parser.add_argument("--category", "-c", help="Category to search")
    search_parser.add_argument("--city", help="City to search")
    search_parser.add_argument("--limit", type=int, default=20)
    
    args = parser.parse_args()
    
    db = LeadDatabase()
    exporter = LeadExporter(db)
    
    if args.command == "import":
        # Find input file
        if args.input:
            input_path = Path(args.input)
        else:
            files = list(DATA_DIR.glob("scrape_*.json"))
            if not files:
                console.print("[red]No scrape files found[/red]")
                return
            input_path = max(files, key=lambda p: p.stat().st_mtime)
            console.print(f"[dim]Using: {input_path}[/dim]")
        
        businesses_data = load_businesses_from_json(input_path)
        
        # Convert to Business objects
        from src.utils.models import Business, Review
        businesses = []
        for data in businesses_data:
            reviews = [Review(**r) for r in data.get("reviews", [])]
            data["reviews"] = reviews
            if "scraped_at" in data and isinstance(data["scraped_at"], str):
                data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])
            businesses.append(Business(**data))
        
        db.insert_businesses(businesses)
    
    elif args.command == "export":
        # Search with filters
        results = db.search(
            category=args.category,
            city=args.city,
            min_rating=args.min_rating,
            max_rating=args.max_rating,
            has_website=False if args.no_website else None,
            limit=args.limit
        )
        
        if not results:
            console.print("[yellow]No leads found matching criteria[/yellow]")
            return
        
        exporter.display_leads(results)
        
        # Export
        if args.format == "csv":
            exporter.export_csv(results, args.output)
        elif args.format == "json":
            exporter.export_json(results, args.output)
        elif args.format == "outreach":
            exporter.export_outreach_list(results, args.output)
    
    elif args.command == "stats":
        stats = db.get_stats()
        
        console.print("\n[bold cyan]📊 Database Statistics[/bold cyan]\n")
        console.print(f"Total Businesses: {stats['total_businesses']}")
        console.print(f"Total Reviews: {stats['total_reviews']}")
        console.print(f"Average Rating: {stats['avg_rating']:.2f}" if stats['avg_rating'] else "Average Rating: N/A")
        console.print(f"Categories: {len(stats['categories'])}")
        
        if stats['cities']:
            console.print("\n[bold]Top Cities:[/bold]")
            for city, count in stats['cities'][:5]:
                console.print(f"  • {city}: {count}")
    
    elif args.command == "search":
        results = db.search(
            category=args.category,
            city=args.city,
            limit=args.limit
        )
        exporter.display_leads(results)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
