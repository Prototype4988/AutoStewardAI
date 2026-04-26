# AutoSteward AI

**Autonomous Data Steward Powered by OpenMetadata AI SDK**

AutoSteward AI transforms data maintenance from a multi-day manual process into a fully autonomous 2-minute workflow.

Traditional data platforms detect issues—but leave engineers to fix them manually.

AutoSteward goes further.
It detects, diagnoses, generates, and applies fixes automatically using AI—powered by OpenMetadata. It integrates with OpenMetadata for lineage tracing and applies fixes directly to your PostgreSQL database, transforming multi-day manual processes into 2-minute autonomous workflows.

## 💡 Why This Matters

Data teams spend a majority of their time:

- Debugging broken pipelines
- Tracing data quality issues across lineage
- Fixing schema and data inconsistencies manually

Existing tools stop at alerting.

👉 AutoSteward turns metadata into action.

## ⚙️ What AutoSteward Does

AutoSteward is an intelligent AI agent that:

- Detects data quality issues using OpenMetadata
- Diagnoses root causes using lineage
- Generates context-aware SQL fixes using AI
- Applies fixes safely with approval
- Verifies results using real data
## 🚀 Key Features

- **Autonomous Issue Detection**: Continuous 30-second polling for data quality issues
- **AI-Powered Root Cause Analysis**: Uses Llama 3 to diagnose issues with human-friendly explanations
- **Lineage-Aware Fix Generation**: Leverages OpenMetadata lineage to generate context-aware SQL fixes
- **Real SQL Execution**: Applies fixes directly to PostgreSQL with approval workflow
- **Impact Visualization**: Before/after data comparison and analytics dashboard
- **Safety Features**: Rate limiting, rollback capability, full audit trails in OpenMetadata
- **Column Tagging**: Tags fixed columns with `AI.AutoStewardAI fixed` for tracking

## 🏆 Usage of OpenMetadata

AutoSteward AI uses OpenMetadata as its core intelligence layer:

- **Data Quality Signals**: Continuously monitors OpenMetadata tests to detect real-time data issues  
- **Lineage-Based Root Cause Analysis**: Uses lineage to trace issues upstream and identify their origin  
- **Metadata Context for AI**: Leverages entity metadata to generate accurate, context-aware SQL fixes  
- **Column Tagging & Governance**: Tags fixed columns for traceability and audit  
- **Audit Trail Integration**: Stores fix history and actions within OpenMetadata for full visibility  

OpenMetadata is not just used for visualization—it actively drives autonomous decision-making in AutoSteward.

## 📋 Project Structure

```
AutoStewardAI/
├── src/                    # Python source code
│   ├── autosteward_ai.py  # Core AI logic and OpenMetadata integration
│   ├── config_loader.py   # Configuration loader
│   └── dashboard.py       # Streamlit dashboard
├── config/                # Configuration files
│   └── config.yaml        # Main configuration
├── docker/                # Docker files
│   └── docker-compose-postgres.yml
│   └── docker-compose.yml
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🛠️ Tech Stack

- **OpenMetadata**: Data lineage, quality tests, metadata management
- **Ollama (Llama 3)**: Local AI for diagnosis and fix generation
- **PostgreSQL**: Database for data and fix execution
- **Streamlit**: Dashboard UI
- **LangChain**: AI orchestration

## 📦 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Docker and Docker Compose
- OpenMetadata instance running (http://localhost:8585)
- Ollama with Llama 3 model (`ollama pull llama3`)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd AutoStewardAI
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Start PostgreSQL with Jaffle Shop data and Openmetadata**
```bash
cd docker
docker-compose -f docker-compose-postgres.yml up -d
docker-compose -f docker-compose.yml up -d
```

4. **Configure OpenMetadata connection**
Edit `config/config.yaml` with your OpenMetadata credentials.

5. **Start Ollama**
```bash
ollama serve
```

6. **Run the dashboard**
```bash
streamlit run src/dashboard.py
```

## 🎬 Demo Walkthrough

- Detected 127 missing email values  
- Traced root cause using OpenMetadata lineage  
- Applied AI-generated fix  
- **Reduced null values from 127 → 0 in seconds**

1. **Introduce a data quality issue**
```bash
cat sql/setup_jaffle_shop.sql | docker exec -i autosteward-postgres psql -U postgres -d jaffle_shop

cat sql/setup_sample_data.sql | docker exec -i autosteward-postgres psql -U postgres -d jaffle_shop

cat sql/introduce_null_spike.sql | docker exec -i autosteward-postgres psql -U postgres -d jaffle_shop

cat sql/populate_mart_customer.sql | docker exec -i autosteward-postgres psql -U postgres -d jaffle_shop
```

2. **Scan for issues** in the dashboard
3. **View lineage graph** to understand upstream/downstream relationships
4. **Generate AI fix** with confidence score and impact prediction
5. **Approve fix** to execute on PostgreSQL
6. **View before/after comparison** to see the impact
7. **Check analytics dashboard** for fix history

## 📊 Dashboard Features

- **Live Data Issues**: Real-time issue detection with severity scoring
- **Lineage Visualization**: Interactive graph showing data flow
- **AI Diagnosis**: Human-friendly explanations of root causes
- **Fix Preview**: SQL fixes with confidence scores and impact metrics
- **Before/After Comparison**: Side-by-side data view
- **Analytics Dashboard**: Fix history charts and time saved metrics
- **Autonomous Mode**: Continuous scanning with rate limiting

## 🔒 Safety Features

- **Rate Limiting**: Max 10 fixes per hour
- **Approval Workflow**: All fixes require manual approval
- **Rollback Capability**: Instantly revert any applied fix
- **Audit Trails**: Full history stored in OpenMetadata

## 📝 Configuration

Edit `config/config.yaml` to customize:
- OpenMetadata connection settings
- PostgreSQL database credentials
- AI provider (Ollama, OpenAI, Groq)
- Severity scoring parameters
- Rate limiting rules
- Notification settings

## 🎯 Impact

- **Time Saved**: Reduces fix time from days to minutes
- **Autonomy**: Continuous monitoring without manual intervention
- **Accuracy**: AI-powered context-aware fixes
- **Visibility**: Full audit trails and impact metrics

**Built for the OpenMetadata Hackathon** 🏆
