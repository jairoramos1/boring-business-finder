# 🏭 Boring Business Finder

An AI-powered system to discover profitable, underserved local business opportunities by analyzing Google Maps data.

Inspired by [Greg Isenberg's video](https://www.youtube.com/watch?v=A8uAl1wiJBA) featuring James Dickerson (The Boring Marketer).

## 🎯 What It Does

1. **Scrapes Google Maps** - Collects business data for any location/category
2. **Analyzes Opportunities** - Scores niches by review volume, velocity, and sentiment
3. **Extracts Pain Points** - Mines customer complaints for business insights
4. **Generates Content** - Creates newsletter ideas from customer feedback
5. **Builds Lead Lists** - Exports actionable leads for outreach

## 📁 Project Structure

```
boring-business-finder/
├── main.py           # Main CLI - run everything from here
├── src/
│   ├── scraper/      # Google Maps data collection
│   ├── analyzer/     # Review analysis & opportunity scoring
│   ├── content/      # Newsletter & content generation
│   ├── api/          # Lead export & database
│   └── utils/        # Shared utilities & models
├── data/             # Scraped data storage (auto-created)
├── output/           # Generated reports & exports (auto-created)
└── config/           # Configuration files
```

---

## 🚀 Quick Start (5 minutes)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/boring-business-finder.git
cd boring-business-finder
```

### 2. Set up virtual environment and install dependencies

```bash
# Create virtual environment (Python 3.9+ required)
python3 -m venv venv

# Activate virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Get your SerpAPI key (required for real data)

1. Go to [serpapi.com](https://serpapi.com/)
2. Sign up for a free account (100 searches/month free)
3. Copy your API key from the dashboard

### 4. Configure environment

```bash
# Copy the example config
cp config/example.env .env

# Edit .env and add your API key
# On Mac/Linux:
nano .env
# On Windows:
notepad .env
```

Add your key:
```
SERPAPI_KEY=your_actual_api_key_here
```

### 5. Run the full pipeline!

```bash
python main.py pipeline "garage organizers" "Charlotte, NC"
```

---

## 🔑 API Keys Explained

| Key | Required? | Cost | Purpose |
|-----|-----------|------|---------|
| `SERPAPI_KEY` | **Yes** (for real data) | Free tier: 100/month | Scrapes Google Maps |
| `ANTHROPIC_API_KEY` | No | Pay-per-use | Enhanced AI analysis (optional) |

### Without API Keys (Demo Mode)
The system works without any API keys using **demo data** - useful for testing the workflow before committing to an API.

### Getting SerpAPI Key (Recommended)
1. Visit [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
2. Verify your email
3. Go to [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key)
4. Copy the key and add to your `.env` file

---

## 📖 Usage Examples

**Note:** Always activate your virtual environment before running commands:
```bash
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

### Run Complete Pipeline
```bash
# Discover + Analyze + Generate Content + Export Leads
python main.py pipeline "mobile diesel repair" "Austin, TX"
python main.py pipeline "irrigation systems" "Phoenix, AZ"
python main.py pipeline "garage organizers" "Denver, CO"
```

### Step-by-Step Commands
```bash
# Step 1: Discover businesses
python main.py discover "pressure washing" "Miami, FL" --max 50

# Step 2: Analyze opportunity
python main.py analyze --category "pressure washing" --location "Miami, FL"

# Step 3: Generate content ideas
python main.py content

# Step 4: Export leads
python main.py export --format outreach
python main.py export --format csv --no-website  # Only businesses without websites
```

### Get Niche Ideas
```bash
python main.py ideas
```

---

## 📊 Output Files

After running the pipeline, you'll find:

| File | Description |
|------|-------------|
| `data/scrape_*.json` | Raw scraped business data |
| `output/analysis_*.json` | Opportunity scores & metrics |
| `output/content_plan_*.md` | Newsletter topics, email sequences, social posts |
| `output/outreach_*.csv` | Lead list with opportunity notes |

---

## 💰 Business Model Ideas

1. **Lead Generation** - Sell leads to service providers ($100-200/lead)
2. **Niche Newsletters** - Build audiences in underserved markets
3. **Directory Sites** - SEO-optimized local business directories
4. **Consulting** - Help entrepreneurs find opportunities

---

## 🛠 Troubleshooting

### "No API key - using demo data"
Add your SerpAPI key to `.env` file (see setup instructions above)

### "ModuleNotFoundError"
```bash
# Make sure your virtual environment is activated
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Then reinstall dependencies
pip install -r requirements.txt
```

### Virtual environment not activating
```bash
# If activation fails, try recreating the virtual environment
rm -rf venv  # Mac/Linux
# or
rmdir /s venv  # Windows

# Then recreate it
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

---

## 📝 License

MIT License - feel free to use for any purpose.

---

## 🙏 Credits

- Workflow concept: [Greg Isenberg](https://twitter.com/gregisenberg) & [The Boring Marketer](https://twitter.com/boringmarketer)
- Built with: Python, SerpAPI, Rich CLI
- Generated with: Claude Code 🤖
