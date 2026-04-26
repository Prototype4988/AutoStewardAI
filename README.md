# AutoSteward AI

**Autonomous Data Steward Powered by OpenMetadata AI SDK**

AutoSteward AI automatically detects, diagnoses, and fixes data quality issues using AI. It integrates with OpenMetadata for lineage tracing and applies fixes directly to your PostgreSQL database, transforming multi-day manual processes into 2-minute autonomous workflows.

## 🚀 Key Features

- **Autonomous Issue Detection**: Continuous 30-second polling for data quality issues
- **AI-Powered Root Cause Analysis**: Uses Llama 3 to diagnose issues with human-friendly explanations
- **Lineage-Aware Fix Generation**: Leverages OpenMetadata lineage to generate context-aware SQL fixes
- **Real SQL Execution**: Applies fixes directly to PostgreSQL with approval workflow
- **Impact Visualization**: Before/after data comparison and analytics dashboard
- **Safety Features**: Rate limiting, rollback capability, full audit trails in OpenMetadata
- **Column Tagging**: Tags fixed columns with `AI.AutoStewardAI fixed` for tracking

## 🏆 Usage of OpenMetadata

- **GET_ENTITY_LINEAGE API**: Visual lineage graph with upstream/downstream relationships
- **PATCH_ENTITY API**: Stores audit trails in asset descriptions
- **Column Tagging**: Marks fixed columns for governance and tracking
- **Data Quality Integration**: Uses OpenMetadata's test framework for issue detection

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
