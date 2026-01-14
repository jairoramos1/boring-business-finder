#!/usr/bin/env python3
"""
Newsletter Content Generator for Boring Business Finder

Transforms customer complaints and market insights into actionable content:
- Newsletter topic ideas
- Social media posts
- Email sequences
- Directory descriptions
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import config, OpportunityScore, DATA_DIR, OUTPUT_DIR

console = Console()


@dataclass
class ContentIdea:
    """A generated content idea"""
    title: str
    content_type: str  # newsletter, social, email, blog
    hook: str
    key_points: List[str]
    target_audience: str
    call_to_action: str
    source_complaint: Optional[str] = None


@dataclass
class NewsletterPlan:
    """A complete newsletter content plan"""
    niche: str
    location: str
    tagline: str
    ideas: List[ContentIdea] = field(default_factory=list)
    email_sequence: List[Dict[str, str]] = field(default_factory=list)
    social_posts: List[str] = field(default_factory=list)


class ContentGenerator:
    """Generates newsletter and marketing content from business data"""
    
    # Templates for different content types
    NEWSLETTER_TEMPLATES = {
        "problem_solution": {
            "hook": "Tired of {problem}? Here's what the best {niche} providers do differently...",
            "structure": ["Problem statement", "Why it happens", "What to look for", "Action steps"]
        },
        "buyer_guide": {
            "hook": "Before hiring a {niche} in {location}, read this first...",
            "structure": ["What to ask", "Red flags", "Price ranges", "Checklist"]
        },
        "local_spotlight": {
            "hook": "The {location} {niche} scene: What's changing in 2025...",
            "structure": ["Market overview", "Trends", "Top providers", "Consumer tips"]
        },
        "complaint_expose": {
            "hook": "We analyzed {count} reviews of {location} {niche} providers. Here's what customers really say...",
            "structure": ["Data overview", "Top complaints", "What it means", "How to avoid"]
        }
    }
    
    EMAIL_SEQUENCE_TEMPLATES = [
        {
            "subject": "Welcome! Here's your guide to finding the best {niche} in {location}",
            "purpose": "Welcome + deliver lead magnet",
            "day": 0
        },
        {
            "subject": "The #1 mistake people make when hiring {niche}...",
            "purpose": "Problem awareness",
            "day": 2
        },
        {
            "subject": "Real story: How one {location} resident saved $500 on {niche}",
            "purpose": "Social proof + tips",
            "day": 4
        },
        {
            "subject": "Ready to get quotes? Here's our vetted list",
            "purpose": "Conversion - directory/lead gen",
            "day": 7
        }
    ]
    
    def __init__(self):
        self.score: Optional[OpportunityScore] = None
    
    def load_analysis(self, filepath: Path) -> OpportunityScore:
        """Load opportunity analysis from JSON"""
        with open(filepath) as f:
            data = json.load(f)
        
        self.score = OpportunityScore(**data)
        console.print(f"[green]✓ Loaded analysis for {self.score.category} in {self.score.location}[/green]")
        return self.score
    
    def generate_plan(self) -> NewsletterPlan:
        """Generate a complete content plan"""
        if not self.score:
            raise ValueError("No analysis loaded. Call load_analysis() first.")
        
        console.print(f"\n[blue]Generating content plan for:[/blue] {self.score.category}")
        
        plan = NewsletterPlan(
            niche=self.score.category,
            location=self.score.location,
            tagline=self._generate_tagline()
        )
        
        # Generate newsletter ideas
        plan.ideas = self._generate_newsletter_ideas()
        
        # Generate email sequence
        plan.email_sequence = self._generate_email_sequence()
        
        # Generate social posts
        plan.social_posts = self._generate_social_posts()
        
        return plan
    
    def _generate_tagline(self) -> str:
        """Generate a catchy tagline for the newsletter"""
        niche = self.score.category.title()
        location = self.score.location.split(",")[0]
        
        taglines = [
            f"The {location} {niche} Insider",
            f"{niche} Tips for {location} Homeowners",
            f"Your {location} {niche} Guide",
            f"The Smart {location} {niche} Newsletter",
        ]
        
        # Pick based on complaint themes
        if "pricing" in self.score.complaint_themes:
            return f"Save Money on {niche} in {location}"
        elif "reliability" in self.score.complaint_themes:
            return f"Find Reliable {niche} in {location}"
        elif "quality" in self.score.complaint_themes:
            return f"Quality {niche} in {location} - The Insider Guide"
        
        return taglines[0]
    
    def _generate_newsletter_ideas(self) -> List[ContentIdea]:
        """Generate newsletter topic ideas"""
        ideas = []
        niche = self.score.category
        location = self.score.location
        
        # Idea 1: Complaint-based content
        if self.score.common_complaints:
            top_complaint = self.score.common_complaints[0]
            ideas.append(ContentIdea(
                title=f"Why {location} {niche.title()} Customers Are Frustrated (And How to Avoid It)",
                content_type="newsletter",
                hook=f"We analyzed hundreds of reviews. The #1 complaint? {self._summarize_complaint(top_complaint)}",
                key_points=[
                    "What customers are really saying",
                    "Red flags to watch for",
                    "Questions to ask before hiring",
                    "How to verify quality"
                ],
                target_audience=f"{location} homeowners looking for {niche}",
                call_to_action="Get our free vetting checklist",
                source_complaint=top_complaint
            ))
        
        # Idea 2: Buyer's guide
        ideas.append(ContentIdea(
            title=f"The Complete {location} {niche.title()} Buyer's Guide (2025 Edition)",
            content_type="newsletter",
            hook=f"Everything you need to know before hiring a {niche} provider in {location}...",
            key_points=[
                "Average costs in your area",
                "What affects pricing",
                "Timeline expectations",
                "DIY vs Professional decision tree"
            ],
            target_audience=f"First-time {niche} customers in {location}",
            call_to_action="Download our pricing calculator"
        ))
        
        # Idea 3: Theme-based content
        if self.score.complaint_themes:
            theme = self.score.complaint_themes[0]
            theme_titles = {
                "reliability": f"How to Find a {niche.title()} Provider Who Actually Shows Up",
                "pricing": f"Don't Get Overcharged: {niche.title()} Pricing in {location}",
                "quality": f"Quality Check: What Good {niche.title()} Work Looks Like",
                "professionalism": f"Signs of a Professional {niche.title()} Provider",
                "communication": f"Getting Straight Answers from {niche.title()} Companies"
            }
            
            ideas.append(ContentIdea(
                title=theme_titles.get(theme, f"{theme.title()} Issues with {niche.title()} Providers"),
                content_type="newsletter",
                hook=f"{theme.title()} is the #1 issue {location} customers face with {niche} providers...",
                key_points=[
                    f"Why {theme} problems are so common",
                    "Warning signs to spot early",
                    "How to protect yourself",
                    "What to do if things go wrong"
                ],
                target_audience=f"{location} residents researching {niche}",
                call_to_action="Join our vetted provider network"
            ))
        
        # Idea 4: Comparison/ranking content
        ideas.append(ContentIdea(
            title=f"Best {niche.title()} in {location}: What the Reviews Really Say",
            content_type="newsletter",
            hook=f"We dug through {self.score.total_reviews}+ reviews to find the truth about {location} {niche} providers...",
            key_points=[
                "Methodology: How we ranked them",
                "Top performers breakdown",
                "Hidden gems with fewer reviews",
                "Who to avoid (and why)"
            ],
            target_audience=f"Anyone comparing {niche} options in {location}",
            call_to_action="Get quotes from our top-rated providers"
        ))
        
        # Idea 5: Seasonal/timely content
        ideas.append(ContentIdea(
            title=f"When to Hire a {niche.title()} in {location} (Timing Guide)",
            content_type="newsletter", 
            hook=f"The best time to book {niche} in {location} might not be when you think...",
            key_points=[
                "Peak vs off-season pricing",
                "How far ahead to book",
                "Weather considerations",
                "Getting priority scheduling"
            ],
            target_audience=f"Planning-ahead homeowners in {location}",
            call_to_action="Set a reminder for optimal booking time"
        ))
        
        return ideas
    
    def _generate_email_sequence(self) -> List[Dict[str, str]]:
        """Generate email sequence for new subscribers"""
        sequence = []
        niche = self.score.category
        location = self.score.location.split(",")[0]
        
        for template in self.EMAIL_SEQUENCE_TEMPLATES:
            email = {
                "day": template["day"],
                "subject": template["subject"].format(niche=niche, location=location),
                "purpose": template["purpose"],
                "preview": self._generate_email_preview(template["purpose"], niche, location)
            }
            sequence.append(email)
        
        return sequence
    
    def _generate_email_preview(self, purpose: str, niche: str, location: str) -> str:
        """Generate email preview text"""
        previews = {
            "Welcome + deliver lead magnet": f"Thanks for joining! Here's your free guide to finding the best {niche} in {location}...",
            "Problem awareness": f"Most people don't realize this until it's too late. When it comes to {niche}...",
            "Social proof + tips": f"Sarah from {location} was about to make a costly mistake. Then she found our checklist...",
            "Conversion - directory/lead gen": f"Ready to get started? Here are {location}'s highest-rated {niche} providers..."
        }
        return previews.get(purpose, f"More tips about {niche} in {location}...")
    
    def _generate_social_posts(self) -> List[str]:
        """Generate social media post ideas"""
        niche = self.score.category
        location = self.score.location.split(",")[0]
        posts = []
        
        # Post 1: Hook with stat
        posts.append(
            f"🔍 We analyzed {self.score.total_reviews}+ reviews of {location} {niche} companies.\n\n"
            f"The results? {self.score.low_rated_businesses} out of {self.score.total_businesses} have ratings below 4 stars.\n\n"
            f"Here's what customers are saying (thread 🧵)..."
        )
        
        # Post 2: Complaint callout
        if self.score.common_complaints:
            posts.append(
                f"💬 Real review from a {location} {niche} customer:\n\n"
                f'"{self.score.common_complaints[0][:100]}..."\n\n'
                f"Don't let this happen to you. Here's what to look for ⬇️"
            )
        
        # Post 3: Tip format
        posts.append(
            f"🏠 Hiring {niche} in {location}?\n\n"
            f"Ask these 3 questions BEFORE you sign:\n"
            f"1. What's included in the quote?\n"
            f"2. What's your timeline?\n"
            f"3. Can I see recent work photos?\n\n"
            f"Save this for later 📌"
        )
        
        # Post 4: Newsletter promo
        posts.append(
            f"📧 New: The {location} {niche.title()} Insider\n\n"
            f"Weekly tips on:\n"
            f"✅ Finding reliable providers\n"
            f"✅ Avoiding overcharges\n"
            f"✅ Getting quality work\n\n"
            f"Free. Unsubscribe anytime.\n"
            f"Link in bio 👆"
        )
        
        return posts
    
    def _summarize_complaint(self, complaint: str) -> str:
        """Create a short summary of a complaint"""
        # Extract key issue
        keywords = ["late", "never", "expensive", "poor", "rude", "slow", "damaged"]
        for kw in keywords:
            if kw in complaint.lower():
                return f"providers being {kw}"
        return "poor service quality"
    
    def display_plan(self, plan: NewsletterPlan):
        """Display the content plan"""
        console.print(Panel(
            f"[bold]{plan.tagline}[/bold]\n\n"
            f"Niche: {plan.niche.title()}\n"
            f"Location: {plan.location}\n"
            f"Content Ideas: {len(plan.ideas)}\n"
            f"Email Sequence: {len(plan.email_sequence)} emails\n"
            f"Social Posts: {len(plan.social_posts)}",
            title="📰 Newsletter Content Plan",
            border_style="cyan"
        ))
        
        # Newsletter Ideas
        console.print("\n[bold cyan]📝 Newsletter Topic Ideas[/bold cyan]\n")
        for i, idea in enumerate(plan.ideas, 1):
            console.print(Panel(
                f"[bold]{idea.title}[/bold]\n\n"
                f"[dim]Hook:[/dim] {idea.hook}\n\n"
                f"[dim]Key Points:[/dim]\n" + "\n".join(f"  • {p}" for p in idea.key_points) + "\n\n"
                f"[dim]CTA:[/dim] {idea.call_to_action}",
                title=f"Idea #{i}",
                border_style="blue"
            ))
        
        # Email Sequence
        console.print("\n[bold cyan]📧 Welcome Email Sequence[/bold cyan]\n")
        for email in plan.email_sequence:
            console.print(f"  [bold]Day {email['day']}:[/bold] {email['subject']}")
            console.print(f"  [dim]{email['preview'][:80]}...[/dim]\n")
        
        # Social Posts
        console.print("\n[bold cyan]📱 Social Media Posts[/bold cyan]\n")
        for i, post in enumerate(plan.social_posts, 1):
            console.print(Panel(post, title=f"Post #{i}", border_style="magenta"))
    
    def save_plan(self, plan: NewsletterPlan, filename: Optional[str] = None) -> Path:
        """Save content plan to JSON and Markdown"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_niche = re.sub(r'[^\w\-]', '_', plan.niche)
        
        # Save JSON
        json_filename = filename or f"content_plan_{safe_niche}_{timestamp}.json"
        json_path = OUTPUT_DIR / json_filename
        
        # Convert to dict
        plan_dict = {
            "niche": plan.niche,
            "location": plan.location,
            "tagline": plan.tagline,
            "ideas": [asdict(idea) for idea in plan.ideas],
            "email_sequence": plan.email_sequence,
            "social_posts": plan.social_posts,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(json_path, "w") as f:
            json.dump(plan_dict, f, indent=2)
        
        # Save Markdown version
        md_filename = f"content_plan_{safe_niche}_{timestamp}.md"
        md_path = OUTPUT_DIR / md_filename
        
        md_content = self._generate_markdown(plan)
        with open(md_path, "w") as f:
            f.write(md_content)
        
        console.print(f"\n[green]✓ Saved to {json_path}[/green]")
        console.print(f"[green]✓ Saved to {md_path}[/green]")
        
        return md_path
    
    def _generate_markdown(self, plan: NewsletterPlan) -> str:
        """Generate markdown version of content plan"""
        md = f"""# 📰 {plan.tagline}

**Niche:** {plan.niche.title()}  
**Location:** {plan.location}  
**Generated:** {datetime.now().strftime("%Y-%m-%d")}

---

## 📝 Newsletter Topic Ideas

"""
        for i, idea in enumerate(plan.ideas, 1):
            md += f"""### {i}. {idea.title}

**Hook:** {idea.hook}

**Key Points:**
"""
            for point in idea.key_points:
                md += f"- {point}\n"
            
            md += f"""
**Target Audience:** {idea.target_audience}  
**Call to Action:** {idea.call_to_action}

---

"""
        
        md += """## 📧 Welcome Email Sequence

"""
        for email in plan.email_sequence:
            md += f"""### Day {email['day']}: {email['subject']}

*Purpose: {email['purpose']}*

> {email['preview']}

---

"""
        
        md += """## 📱 Social Media Posts

"""
        for i, post in enumerate(plan.social_posts, 1):
            md += f"""### Post {i}

```
{post}
```

---

"""
        
        return md


def find_latest_analysis() -> Optional[Path]:
    """Find most recent analysis file"""
    files = list(OUTPUT_DIR.glob("analysis_*.json"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main():
    """CLI interface for content generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate newsletter content from analysis")
    parser.add_argument("--input", "-i", help="Analysis JSON file (default: latest)")
    parser.add_argument("--save", "-s", action="store_true", help="Save content plan")
    
    args = parser.parse_args()
    
    # Find input
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = find_latest_analysis()
        if not input_path:
            console.print("[red]No analysis files found. Run the analyzer first.[/red]")
            return
        console.print(f"[dim]Using latest analysis: {input_path}[/dim]")
    
    # Generate content
    generator = ContentGenerator()
    generator.load_analysis(input_path)
    
    plan = generator.generate_plan()
    generator.display_plan(plan)
    
    if args.save:
        generator.save_plan(plan)


if __name__ == "__main__":
    main()
