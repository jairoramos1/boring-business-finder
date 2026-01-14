#!/usr/bin/env python3
"""
Opportunity Analyzer for Boring Business Finder

Analyzes scraped business data to score market opportunities based on:
- Review volume (market demand)
- Review velocity (growth rate)
- Rating gaps (quality problems = opportunity)
- Digital presence gaps (no website = opportunity)
- Pain point extraction from negative reviews
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from dataclasses import asdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import config, Business, Review, OpportunityScore, DATA_DIR, OUTPUT_DIR

console = Console()


class OpportunityAnalyzer:
    """Analyzes business data to find market opportunities"""
    
    # Common complaint keywords to look for
    COMPLAINT_KEYWORDS = [
        "late", "never showed", "no show", "unprofessional", "rude",
        "expensive", "overpriced", "ripoff", "rip off", "scam",
        "poor quality", "sloppy", "messy", "damaged", "broke",
        "no response", "didn't return", "ignored", "ghosted",
        "took forever", "slow", "delayed", "waited",
        "wouldn't recommend", "avoid", "terrible", "worst",
        "miscommunication", "wrong", "mistake", "error"
    ]
    
    # Complaint categories for theming
    COMPLAINT_THEMES = {
        "reliability": ["late", "never showed", "no show", "didn't show", "took forever", "slow", "delayed", "waited"],
        "professionalism": ["unprofessional", "rude", "ignored", "ghosted", "no response", "didn't return"],
        "pricing": ["expensive", "overpriced", "ripoff", "rip off", "scam", "too much"],
        "quality": ["poor quality", "sloppy", "messy", "damaged", "broke", "wrong", "mistake"],
        "communication": ["miscommunication", "no response", "didn't call", "no update", "couldn't reach"]
    }
    
    def __init__(self):
        self.businesses: List[Business] = []
    
    def load_data(self, filepath: Path) -> List[Business]:
        """Load scraped business data from JSON file"""
        with open(filepath) as f:
            data = json.load(f)
        
        businesses = []
        for biz_data in data.get("businesses", []):
            # Convert reviews
            reviews = []
            for r in biz_data.get("reviews", []):
                reviews.append(Review(
                    rating=r.get("rating", 3),
                    text=r.get("text", ""),
                    author=r.get("author")
                ))
            
            biz_data["reviews"] = reviews
            
            # Handle datetime
            if "scraped_at" in biz_data:
                if isinstance(biz_data["scraped_at"], str):
                    biz_data["scraped_at"] = datetime.fromisoformat(biz_data["scraped_at"])
            
            businesses.append(Business(**biz_data))
        
        self.businesses = businesses
        console.print(f"[green]✓ Loaded {len(businesses)} businesses[/green]")
        return businesses
    
    def analyze(self, category: str, location: str) -> OpportunityScore:
        """
        Analyze loaded businesses and calculate opportunity score
        
        Returns an OpportunityScore with all metrics calculated
        """
        if not self.businesses:
            raise ValueError("No businesses loaded. Call load_data() first.")
        
        console.print(f"\n[blue]Analyzing opportunity for:[/blue] {category} in {location}\n")
        
        score = OpportunityScore(category=category, location=location)
        
        # Basic metrics
        score.total_businesses = len(self.businesses)
        score.total_reviews = sum(b.review_count for b in self.businesses)
        score.avg_reviews_per_business = score.total_reviews / max(score.total_businesses, 1)
        
        # Rating analysis
        ratings = [b.rating for b in self.businesses if b.rating]
        score.avg_rating = sum(ratings) / max(len(ratings), 1) if ratings else 0
        score.low_rated_businesses = sum(1 for b in self.businesses if b.rating and b.rating < 4.0)
        
        # Website gap
        score.businesses_without_website = sum(1 for b in self.businesses if not b.website)
        
        # Extract complaints from negative reviews
        all_complaints = []
        for biz in self.businesses:
            for review in biz.negative_reviews:
                complaints = self._extract_complaints(review.text)
                all_complaints.extend(complaints)
        
        score.common_complaints = self._get_top_complaints(all_complaints, limit=10)
        score.complaint_themes = self._categorize_complaints(all_complaints)
        
        # Calculate final score
        score.calculate_score()
        
        return score
    
    def _extract_complaints(self, text: str) -> List[str]:
        """Extract complaint keywords from review text"""
        text_lower = text.lower()
        found = []
        
        for keyword in self.COMPLAINT_KEYWORDS:
            if keyword in text_lower:
                # Extract the sentence containing the keyword
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        found.append(sentence.strip())
                        break
        
        return found
    
    def _get_top_complaints(self, complaints: List[str], limit: int = 10) -> List[str]:
        """Get the most common complaints"""
        # Simple deduplication by similarity
        unique = []
        for c in complaints:
            is_duplicate = False
            c_words = set(c.lower().split())
            for existing in unique:
                existing_words = set(existing.lower().split())
                overlap = len(c_words & existing_words) / max(len(c_words | existing_words), 1)
                if overlap > 0.5:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(c)
        
        return unique[:limit]
    
    def _categorize_complaints(self, complaints: List[str]) -> List[str]:
        """Categorize complaints into themes"""
        theme_counts = Counter()
        
        for complaint in complaints:
            complaint_lower = complaint.lower()
            for theme, keywords in self.COMPLAINT_THEMES.items():
                if any(kw in complaint_lower for kw in keywords):
                    theme_counts[theme] += 1
        
        # Return themes sorted by frequency
        return [theme for theme, _ in theme_counts.most_common()]
    
    def display_analysis(self, score: OpportunityScore):
        """Display analysis results in a formatted way"""
        
        # Score color
        if score.opportunity_score >= 70:
            score_color = "green"
            score_emoji = "🔥"
        elif score.opportunity_score >= 50:
            score_color = "yellow"
            score_emoji = "👀"
        else:
            score_color = "red"
            score_emoji = "⚠️"
        
        # Header panel
        console.print(Panel(
            f"[bold {score_color}]{score_emoji} Opportunity Score: {score.opportunity_score}/100[/bold {score_color}]",
            title=f"[bold]{score.category.title()}[/bold] in {score.location}",
            border_style=score_color
        ))
        
        # Metrics table
        metrics_table = Table(show_header=True, header_style="bold cyan")
        metrics_table.add_column("Metric")
        metrics_table.add_column("Value", justify="right")
        metrics_table.add_column("Signal", justify="center")
        
        # Total businesses
        biz_signal = "🟢" if score.total_businesses < 20 else "🟡" if score.total_businesses < 50 else "🔴"
        metrics_table.add_row("Total Businesses", str(score.total_businesses), biz_signal + " (fewer = opportunity)")
        
        # Total reviews (market demand)
        rev_signal = "🟢" if score.total_reviews > 100 else "🟡" if score.total_reviews > 50 else "🔴"
        metrics_table.add_row("Total Reviews", str(score.total_reviews), rev_signal + " (more = demand)")
        
        # Average rating
        rating_signal = "🟢" if score.avg_rating < 4.0 else "🟡" if score.avg_rating < 4.3 else "🔴"
        metrics_table.add_row("Avg Rating", f"{score.avg_rating:.1f}", rating_signal + " (lower = gap)")
        
        # Low-rated businesses
        low_pct = (score.low_rated_businesses / max(score.total_businesses, 1)) * 100
        low_signal = "🟢" if low_pct > 30 else "🟡" if low_pct > 15 else "🔴"
        metrics_table.add_row("Low-Rated (<4★)", f"{score.low_rated_businesses} ({low_pct:.0f}%)", low_signal)
        
        # No website
        web_pct = (score.businesses_without_website / max(score.total_businesses, 1)) * 100
        web_signal = "🟢" if web_pct > 30 else "🟡" if web_pct > 15 else "🔴"
        metrics_table.add_row("No Website", f"{score.businesses_without_website} ({web_pct:.0f}%)", web_signal + " (digital gap)")
        
        console.print(metrics_table)
        
        # Complaint themes
        if score.complaint_themes:
            console.print("\n[bold yellow]📋 Top Complaint Themes:[/bold yellow]")
            for i, theme in enumerate(score.complaint_themes[:5], 1):
                console.print(f"  {i}. {theme.title()}")
        
        # Top complaints
        if score.common_complaints:
            console.print("\n[bold yellow]💬 Sample Customer Complaints:[/bold yellow]")
            for complaint in score.common_complaints[:5]:
                console.print(f"  • \"{complaint[:100]}{'...' if len(complaint) > 100 else ''}\"")
        
        # Recommendation
        console.print("\n")
        if score.opportunity_score >= 70:
            console.print(Panel(
                "[green]HIGH OPPORTUNITY[/green]\n\n"
                "This niche shows strong signals:\n"
                "• Limited competition\n"
                "• Quality gaps in existing providers\n"
                "• Clear customer pain points to address\n\n"
                "[bold]Recommended next steps:[/bold]\n"
                "1. Create a niche newsletter targeting this market\n"
                "2. Build a simple directory/lead-gen site\n"
                "3. Reach out to existing providers about lead generation",
                title="💡 Recommendation",
                border_style="green"
            ))
        elif score.opportunity_score >= 50:
            console.print(Panel(
                "[yellow]MODERATE OPPORTUNITY[/yellow]\n\n"
                "This niche has potential but consider:\n"
                "• More competitive than ideal niches\n"
                "• May need stronger differentiation\n\n"
                "[bold]Recommended:[/bold] Research 2-3 more niches before committing",
                title="💡 Recommendation",
                border_style="yellow"
            ))
        else:
            console.print(Panel(
                "[red]LOW OPPORTUNITY[/red]\n\n"
                "This niche may be too competitive or saturated.\n"
                "Consider searching for less obvious categories.",
                title="💡 Recommendation", 
                border_style="red"
            ))
    
    def save_analysis(self, score: OpportunityScore, filename: Optional[str] = None) -> Path:
        """Save analysis results to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_category = re.sub(r'[^\w\-]', '_', score.category)
            filename = f"analysis_{safe_category}_{timestamp}.json"
        
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w") as f:
            json.dump(asdict(score), f, indent=2)
        
        console.print(f"\n[green]✓ Analysis saved to {filepath}[/green]")
        return filepath


def find_latest_scrape() -> Optional[Path]:
    """Find the most recent scrape file"""
    scrape_files = list(DATA_DIR.glob("scrape_*.json"))
    if not scrape_files:
        return None
    return max(scrape_files, key=lambda p: p.stat().st_mtime)


def main():
    """CLI interface for the analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze business data for opportunities")
    parser.add_argument("--input", "-i", help="Input JSON file (default: latest scrape)")
    parser.add_argument("--category", "-c", default="local services", help="Category name")
    parser.add_argument("--location", "-l", default="Unknown", help="Location name")
    parser.add_argument("--save", "-s", action="store_true", help="Save analysis to file")
    
    args = parser.parse_args()
    
    # Find input file
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = find_latest_scrape()
        if not input_path:
            console.print("[red]No scrape files found. Run the scraper first.[/red]")
            return
        console.print(f"[dim]Using latest scrape: {input_path}[/dim]")
    
    # Run analysis
    analyzer = OpportunityAnalyzer()
    analyzer.load_data(input_path)
    
    score = analyzer.analyze(args.category, args.location)
    analyzer.display_analysis(score)
    
    if args.save:
        analyzer.save_analysis(score)


if __name__ == "__main__":
    main()
