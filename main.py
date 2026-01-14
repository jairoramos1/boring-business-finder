#!/usr/bin/env python3
"""
Boring Business Finder - Main CLI

A complete pipeline to find profitable local business opportunities:
1. Scrape Google Maps for business data
2. Analyze opportunity scores
3. Generate newsletter content
4. Export leads for outreach

Usage:
    python main.py discover "garage organizers" "Charlotte, NC"
    python main.py analyze
    python main.py content
    python main.py export --format outreach
    python main.py pipeline "irrigation systems" "Austin, TX"
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import argparse

from src.scraper import GoogleMapsScraper
from src.analyzer import OpportunityAnalyzer
from src.content import ContentGenerator
from src.api import LeadDatabase, LeadExporter
from src.utils import DATA_DIR, OUTPUT_DIR, BusinessCategory

console = Console()


def show_banner():
    """Display application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   🏭  BORING BUSINESS FINDER                                 ║
    ║                                                              ║
    ║   Find profitable, overlooked local business opportunities   ║
    ║   using AI-powered Google Maps analysis                      ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")


def cmd_discover(args):
    """Discover businesses in a niche"""
    console.print(f"\n[bold blue]🔍 Discovering:[/bold blue] {args.query} in {args.location}\n")
    
    scraper = GoogleMapsScraper()
    businesses = scraper.search(args.query, args.location, args.max)
    
    scraper.display_results(businesses)
    
    # Save results
    filepath = scraper.save_results(businesses)
    
    # Import to database
    if args.save_db:
        db = LeadDatabase()
        from src.utils.models import Business, Review
        biz_objects = []
        for data in [b.__dict__ for b in businesses]:
            reviews = data.get("reviews", [])
            data["reviews"] = reviews
            biz_objects.append(Business(**data))
        db.insert_businesses(biz_objects)
    
    return filepath


def cmd_analyze(args):
    """Analyze scraped data for opportunities"""
    console.print("\n[bold blue]📊 Analyzing opportunities...[/bold blue]\n")
    
    analyzer = OpportunityAnalyzer()
    
    # Find latest scrape or use specified file
    if args.input:
        input_path = Path(args.input)
    else:
        scrape_files = list(DATA_DIR.glob("scrape_*.json"))
        if not scrape_files:
            console.print("[red]No scrape files found. Run 'discover' first.[/red]")
            return None
        input_path = max(scrape_files, key=lambda p: p.stat().st_mtime)
        console.print(f"[dim]Using: {input_path.name}[/dim]")
    
    analyzer.load_data(input_path)
    
    score = analyzer.analyze(
        category=args.category or "local services",
        location=args.location or "Unknown"
    )
    
    analyzer.display_analysis(score)
    
    # Save analysis
    filepath = analyzer.save_analysis(score)
    
    return filepath


def cmd_content(args):
    """Generate newsletter content"""
    console.print("\n[bold blue]📝 Generating content...[/bold blue]\n")
    
    generator = ContentGenerator()
    
    # Find latest analysis
    if args.input:
        input_path = Path(args.input)
    else:
        analysis_files = list(OUTPUT_DIR.glob("analysis_*.json"))
        if not analysis_files:
            console.print("[red]No analysis files found. Run 'analyze' first.[/red]")
            return None
        input_path = max(analysis_files, key=lambda p: p.stat().st_mtime)
        console.print(f"[dim]Using: {input_path.name}[/dim]")
    
    generator.load_analysis(input_path)
    plan = generator.generate_plan()
    
    generator.display_plan(plan)
    
    # Save plan
    filepath = generator.save_plan(plan)
    
    return filepath


def cmd_export(args):
    """Export leads"""
    console.print("\n[bold blue]📤 Exporting leads...[/bold blue]\n")
    
    db = LeadDatabase()
    exporter = LeadExporter(db)
    
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
        return None
    
    exporter.display_leads(results)
    
    # Export based on format
    if args.format == "csv":
        filepath = exporter.export_csv(results, args.output)
    elif args.format == "json":
        filepath = exporter.export_json(results, args.output)
    elif args.format == "outreach":
        filepath = exporter.export_outreach_list(results, args.output)
    
    return filepath


def cmd_pipeline(args):
    """Run the complete pipeline"""
    show_banner()
    
    console.print(Panel(
        f"[bold]Running full pipeline for:[/bold]\n\n"
        f"🎯 Niche: {args.query}\n"
        f"📍 Location: {args.location}",
        title="🚀 Pipeline Started",
        border_style="green"
    ))
    
    results = {}
    
    # Step 1: Discover
    console.print("\n" + "="*60)
    console.print("[bold]STEP 1/4: Discovering businesses[/bold]")
    console.print("="*60)
    
    scraper = GoogleMapsScraper()
    businesses = scraper.search(args.query, args.location, args.max)
    scraper.display_results(businesses)
    scrape_path = scraper.save_results(businesses)
    results["scrape"] = scrape_path
    
    # Step 2: Analyze
    console.print("\n" + "="*60)
    console.print("[bold]STEP 2/4: Analyzing opportunity[/bold]")
    console.print("="*60)
    
    analyzer = OpportunityAnalyzer()
    analyzer.load_data(scrape_path)
    score = analyzer.analyze(args.query, args.location)
    analyzer.display_analysis(score)
    analysis_path = analyzer.save_analysis(score)
    results["analysis"] = analysis_path
    
    # Step 3: Generate content
    console.print("\n" + "="*60)
    console.print("[bold]STEP 3/4: Generating content[/bold]")
    console.print("="*60)
    
    generator = ContentGenerator()
    generator.load_analysis(analysis_path)
    plan = generator.generate_plan()
    generator.display_plan(plan)
    content_path = generator.save_plan(plan)
    results["content"] = content_path
    
    # Step 4: Export leads
    console.print("\n" + "="*60)
    console.print("[bold]STEP 4/4: Exporting leads[/bold]")
    console.print("="*60)
    
    db = LeadDatabase()
    from src.utils.models import Business, Review
    biz_objects = []
    for biz in businesses:
        biz_objects.append(biz)
    db.insert_businesses(biz_objects)
    
    exporter = LeadExporter(db)
    leads = db.search(limit=100)
    if leads:
        export_path = exporter.export_outreach_list(leads)
        results["leads"] = export_path
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold green]✅ PIPELINE COMPLETE[/bold green]")
    console.print("="*60)
    
    console.print(Panel(
        f"[bold]Generated Files:[/bold]\n\n"
        f"📊 Scrape Data: {results.get('scrape', 'N/A')}\n"
        f"📈 Analysis: {results.get('analysis', 'N/A')}\n"
        f"📝 Content Plan: {results.get('content', 'N/A')}\n"
        f"📤 Outreach List: {results.get('leads', 'N/A')}",
        title="📁 Output Files",
        border_style="cyan"
    ))
    
    # Next steps
    if score.opportunity_score >= 70:
        console.print(Panel(
            "[bold green]HIGH OPPORTUNITY DETECTED![/bold green]\n\n"
            "Recommended next steps:\n\n"
            "1. 📧 Start a niche newsletter with the generated content\n"
            "2. 🌐 Build a simple directory site for lead capture\n"
            "3. 📞 Reach out to low-rated businesses about lead gen\n"
            "4. 📱 Post the social content to build an audience",
            title="🎯 Next Steps",
            border_style="green"
        ))
    
    return results


def cmd_ideas(args):
    """Show boring business niche ideas"""
    console.print("\n[bold cyan]💡 Boring Business Niche Ideas[/bold cyan]\n")
    
    categories = [
        ("🚗 Automotive", ["mobile mechanic", "mobile diesel repair", "mobile detailing", "windshield repair"]),
        ("🏠 Home Services", ["garage organizers", "gutter cleaning", "pressure washing", "window cleaning"]),
        ("🌳 Outdoor", ["irrigation systems", "tree service", "lawn care", "fence installation"]),
        ("🔧 Repair", ["appliance repair", "locksmith", "handyman services", "HVAC maintenance"]),
        ("🧹 Cleaning", ["carpet cleaning", "pool service", "junk removal", "chimney sweep"]),
        ("🐛 Specialty", ["pest control", "mold remediation", "septic services", "wildlife removal"]),
    ]
    
    for category_name, niches in categories:
        console.print(f"\n[bold]{category_name}[/bold]")
        for niche in niches:
            console.print(f"  • {niche}")
    
    console.print("\n[dim]Tip: Look for niches with high demand + poor existing quality[/dim]")
    console.print("[dim]Run: python main.py pipeline \"<niche>\" \"<city>, <state>\"[/dim]\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Find profitable boring business opportunities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run the full pipeline
    python main.py pipeline "garage organizers" "Charlotte, NC"
    
    # Step by step
    python main.py discover "irrigation systems" "Austin, TX" --max 50
    python main.py analyze --category "irrigation systems" --location "Austin, TX"
    python main.py content
    python main.py export --format outreach
    
    # Get niche ideas
    python main.py ideas
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Scrape Google Maps for businesses")
    discover_parser.add_argument("query", help="Business type to search")
    discover_parser.add_argument("location", help="City, State to search")
    discover_parser.add_argument("--max", "-m", type=int, default=20, help="Max results")
    discover_parser.add_argument("--save-db", action="store_true", help="Save to database")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze opportunity score")
    analyze_parser.add_argument("--input", "-i", help="Input scrape JSON file")
    analyze_parser.add_argument("--category", "-c", help="Category name")
    analyze_parser.add_argument("--location", "-l", help="Location name")
    
    # Content command
    content_parser = subparsers.add_parser("content", help="Generate newsletter content")
    content_parser.add_argument("--input", "-i", help="Input analysis JSON file")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export leads")
    export_parser.add_argument("--format", "-f", choices=["csv", "json", "outreach"], default="csv")
    export_parser.add_argument("--category", "-c", help="Filter by category")
    export_parser.add_argument("--city", help="Filter by city")
    export_parser.add_argument("--min-rating", type=float, help="Minimum rating")
    export_parser.add_argument("--max-rating", type=float, help="Maximum rating")
    export_parser.add_argument("--no-website", action="store_true", help="Only without website")
    export_parser.add_argument("--limit", type=int, default=100, help="Max results")
    export_parser.add_argument("--output", "-o", help="Output filename")
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Run complete pipeline")
    pipeline_parser.add_argument("query", help="Business type to search")
    pipeline_parser.add_argument("location", help="City, State to search")
    pipeline_parser.add_argument("--max", "-m", type=int, default=20, help="Max results")
    
    # Ideas command
    ideas_parser = subparsers.add_parser("ideas", help="Show niche ideas")
    
    args = parser.parse_args()
    
    if not args.command:
        show_banner()
        parser.print_help()
        return
    
    # Route to appropriate command
    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "content":
        cmd_content(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "ideas":
        cmd_ideas(args)


if __name__ == "__main__":
    main()
