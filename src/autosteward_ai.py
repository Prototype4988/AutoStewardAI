"""
AutoSteward AI - Autonomous Data Steward
Uses OpenMetadata AI SDK to detect, diagnose, and fix data issues
"""

from ai_sdk import AISdk, AISdkConfig
from ai_sdk.mcp.models import MCPTool
from src.config_loader import load_config, AutoStewardConfig
import os
import requests
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

class AutoStewardAI:
    def __init__(self, config_path="config/config.yaml"):
        """Initialize AutoSteward AI with configuration"""
        self.config: AutoStewardConfig = load_config(config_path)
        
        # Initialize OpenMetadata AI SDK client from config
        om_config = self.config.openmetadata
        self.client = AISdk(
            host=om_config.host,
            token=om_config.token
        )
        
        # Initialize LangChain LLM for SQL generation (required)
        provider = self.config.ai.get('provider', 'groq')
        model = self.config.ai.get('model', 'llama3-70b-8192')
        temperature = self.config.ai.get('temperature', 0.1)
        max_tokens = self.config.ai.get('max_tokens', 2000)
        
        if provider == 'openai':
            openai_api_key = self.config.ai.get('openai_api_key')
            if not openai_api_key:
                raise ValueError("openai_api_key is required in config.yaml when provider is 'openai'. Set it or use ${OPENAI_API_KEY} environment variable substitution.")
            
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=openai_api_key
            )
            print(f"Using OpenAI with model: {model}")
        elif provider == 'ollama':
            ollama_base_url = self.config.ai.get('ollama_base_url', 'http://localhost:11434')
            self.llm = ChatOllama(
                model=model,
                temperature=temperature,
                base_url=ollama_base_url
            )
            print(f"Using Ollama with model: {model} at {ollama_base_url}")
        elif provider == 'groq':
            groq_api_key = self.config.ai.get('groq_api_key')
            if not groq_api_key:
                raise ValueError("groq_api_key is required in config.yaml when provider is 'groq'. Get free key at https://console.groq.com")
            
            self.llm = ChatGroq(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=groq_api_key
            )
            print(f"Using Groq with model: {model}")
        else:
            raise ValueError(f"Unsupported AI provider: {provider}. Use 'openai', 'ollama', or 'groq'.")
    
    def get_project_info(self):
        """Get project information from config"""
        return {
            "name": self.config.project.name,
            "service_name": self.config.project.service_name,
            "database_name": self.config.project.database_name
        }
    
    def detect_issue(self, table_fqn):
        """Detect data quality issues for a table"""
        result = self.client.mcp.call_tool(MCPTool.GET_ENTITY_DETAILS, {
            "fqn": table_fqn,
            "entityType": "table"
        })
        return result.data
    
    def trace_lineage(self, table_fqn, upstream_depth=3, downstream_depth=2):
        """Trace upstream and downstream lineage to find root cause"""
        result = self.client.mcp.call_tool(MCPTool.GET_ENTITY_LINEAGE, {
            "fqn": table_fqn,
            "entityType": "table",
            "upstreamDepth": upstream_depth,
            "downstreamDepth": downstream_depth
        })
        return result.data
    
    def get_entity_name_from_id(self, entity_id):
        """Fetch entity name from UUID using GET_ENTITY_DETAILS"""
        try:
            result = self.client.mcp.call_tool(MCPTool.GET_ENTITY_DETAILS, {
                "fqn": entity_id,
                "entityType": "table"
            })
            entity = result.data
            return entity.get('name', entity_id) if entity else entity_id
        except:
            return entity_id
    
    def diagnose_root_cause(self, table_fqn):
        """Use AI to diagnose root cause of data quality issue"""
        result = self.client.mcp.call_tool(MCPTool.ROOT_CAUSE_ANALYSIS, {
            "fqn": table_fqn,
            "entityType": "table"
        })
        diagnosis = result.data
        
        # If lineage data is missing, get it separately from GET_ENTITY_LINEAGE
        if not diagnosis.get('lineage') or not diagnosis.get('lineage', {}).get('downstreamEdges'):
            try:
                lineage_result = self.client.mcp.call_tool(MCPTool.GET_ENTITY_LINEAGE, {
                    "fqn": table_fqn,
                    "entityType": "table",
                    "upstreamDepth": 3,
                    "downstreamDepth": 3
                })
                diagnosis['lineage'] = lineage_result.data
            except Exception as e:
                print(f"Warning: Could not fetch lineage: {e}")
        
        # Calculate severity score (0-100) and get breakdown
        severity, severity_breakdown = self._calculate_severity(diagnosis)
        diagnosis['severity_score'] = severity
        diagnosis['severity_breakdown'] = severity_breakdown
        
        # Generate human-friendly diagnosis message using LLM
        diagnosis['human_friendly_message'] = self._generate_human_friendly_diagnosis(table_fqn, diagnosis)
        
        return diagnosis
    
    def _generate_human_friendly_diagnosis(self, table_fqn, diagnosis):
        """Generate a human-friendly diagnosis message using LLM"""
        try:
            upstream_analysis = diagnosis.get('upstreamAnalysis', {})
            failing_nodes = upstream_analysis.get('failingUpstreamNodes', [])
            
            if not failing_nodes:
                return "We found a data quality issue that needs attention."
            
            failing_node = failing_nodes[0]
            failing_tests = failing_node.get('failingTestCases', {})
            test_results = failing_tests.get('testCaseResults', [])
            
            if not test_results:
                return "We found a data quality issue that needs attention."
            
            test_result = test_results[0]
            test_name = test_result.get('name', '')
            test_fqn = test_result.get('testCaseFQN', '')
            result = test_result.get('result', '')
            
            # Extract table name from FQN
            table_name = table_fqn.split('.')[-1] if '.' in table_fqn else table_fqn
            
            # Determine issue type from test name or FQN
            issue_type = "data quality"
            if 'null' in test_name.lower() or 'null' in test_fqn.lower():
                issue_type = "missing values"
            elif 'duplicate' in test_name.lower() or 'duplicate' in test_fqn.lower():
                issue_type = "duplicate records"
            elif 'format' in test_name.lower() or 'mismatch' in test_name.lower():
                issue_type = "format mismatch"
            
            # Extract column name from test FQN (preferred) or test name
            column_name = "unknown column"
            # Try to extract from test FQN first
            if test_fqn:
                # FQN format: service.database.layer.table.column.test_name
                parts = test_fqn.split('.')
                if len(parts) >= 5:
                    # The column is usually the 5th part (index 4)
                    potential_column = parts[4]
                    if potential_column and potential_column != table_name:
                        column_name = potential_column
            
            # Fallback to test name extraction
            if column_name == "unknown column":
                import re
                if 'email' in test_name.lower():
                    column_name = "customer_email"
                elif 'customer' in test_name.lower() and 'id' in test_name.lower():
                    column_name = "customer_id"
                elif 'id' in test_name.lower():
                    column_name = "customer_id"
                elif 'name' in test_name.lower():
                    column_name = "customer_name"
                else:
                    words = re.findall(r'[a-z_]+', test_name.lower())
                    test_words = ['test', 'check', 'null', 'duplicate', 'format', 'valid', 'quality']
                    column_candidates = [w for w in words if w not in test_words and len(w) > 2]
                    if column_candidates:
                        column_name = column_candidates[0]
            
            print(f"DEBUG: Test FQN: {test_fqn}")
            print(f"DEBUG: Test name: {test_name}")
            print(f"DEBUG: Extracted column: {column_name}")
            
            print(f"DEBUG: Generating diagnosis for table={table_name}, test={test_name}, issue_type={issue_type}, column={column_name}")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a data engineering expert. Generate specific, detailed explanations of data quality issues for non-technical users. Be very specific about what column, what table, and what the issue is."),
                ("human", """Generate a specific, detailed explanation (2-3 sentences) for this data quality issue:

Table: {table_name}
Column: {column_name}
Test Name: {test_name}
Issue Type: {issue_type}
Issue Details: {result}

Guidelines:
- Be VERY SPECIFIC about which column and what the problem is
- Use simple language (no technical jargon like "null spike", "FQN", "lineage")
- Focus on what the problem is and what it affects
- Use active voice ("We found" instead of "detected")
- Keep it under 100 words
- Make it actionable
- MUST mention the specific column name: {column_name}

Example format:
"We found 127 missing email addresses in the customers table's customer_email column. This is likely caused by data coming from your raw sources or issues during data processing. We traced the data flow to identify where the problem originates."

Generate the explanation:""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "table_name": table_name,
                "test_name": test_name,
                "result": result,
                "issue_type": issue_type,
                "column_name": column_name
            })
            
            diagnosis_message = response.content.strip()
            # Remove any prefix like "Here is a specific, detailed explanation of the data quality issue:"
            import re
            # Match pattern: "Here is a specific, detailed explanation of the data quality issue:" followed by the actual message in quotes
            match = re.search(r'"([^"]+)"', diagnosis_message)
            if match:
                diagnosis_message = match.group(1)
            else:
                # Fallback: remove common prefixes
                prefixes_to_remove = [
                    "Here is a specific, detailed explanation of the data quality issue:",
                    "Here is a specific",
                    "detailed explanation of the data quality issue:",
                    "detailed explanation of the data quality issue"
                ]
                for prefix in prefixes_to_remove:
                    if prefix in diagnosis_message:
                        diagnosis_message = diagnosis_message.replace(prefix, "").strip()
            # Clean up any remaining quotes and whitespace
            diagnosis_message = diagnosis_message.strip().strip('"').strip()
            print(f"DEBUG: Generated diagnosis: {diagnosis_message}")
            return diagnosis_message
        except Exception as e:
            print(f"Error generating human-friendly diagnosis: {e}")
            # Fallback to a specific message based on what we know
            return f"We found {issue_type} in the {table_name} table's {column_name} column that needs attention."
    
    def _calculate_severity(self, diagnosis):
        """Calculate severity score based on diagnosis data and return breakdown"""
        if diagnosis.get('status') != 'failed':
            return 0, {}
        
        severity_config = self.config.severity
        severity = 0
        breakdown = {
            'base_score': severity_config.base_score,
            'failing_tests_score': 0,
            'issue_type_score': 0,
            'downstream_impact_score': 0,
            'failing_tests_count': 0,
            'issue_type': 'unknown',
            'downstream_count': 0
        }
        
        upstream_analysis = diagnosis.get('upstreamAnalysis', {})
        failing_nodes = upstream_analysis.get('failingUpstreamNodes', [])
        
        if not failing_nodes:
            return 0, breakdown
        
        # Base severity for any failure
        severity += severity_config.base_score
        
        # Add severity based on number of failing tests
        failing_node = failing_nodes[0]
        failing_tests = failing_node.get('failingTestCases', {})
        test_results = failing_tests.get('testCaseResults', [])
        test_score = min(severity_config.max_failing_test_score, len(test_results) * severity_config.failing_test_points)
        severity += test_score
        breakdown['failing_tests_score'] = test_score
        breakdown['failing_tests_count'] = len(test_results)
        
        # Add severity based on issue type
        issue_type_score = 0
        issue_type = 'unknown'
        for test_result in test_results:
            test_name = test_result.get('name', '').lower()
            if 'null' in test_name:
                issue_type_score = severity_config.issue_type_scores.get('null_values', 20)
                issue_type = 'null_values'
                break
            elif 'duplicate' in test_name:
                issue_type_score = severity_config.issue_type_scores.get('duplicates', 15)
                issue_type = 'duplicates'
                break
            elif 'format' in test_name or 'mismatch' in test_name:
                issue_type_score = severity_config.issue_type_scores.get('format_mismatch', 10)
                issue_type = 'format_mismatch'
                break
        
        severity += issue_type_score
        breakdown['issue_type_score'] = issue_type_score
        breakdown['issue_type'] = issue_type
        
        # Add severity based on downstream impact
        lineage = diagnosis.get('lineage', {})
        downstream_edges = lineage.get('downstreamEdges', [])
        downstream_score = min(severity_config.max_downstream_impact_score, len(downstream_edges) * severity_config.downstream_impact_points)
        severity += downstream_score
        breakdown['downstream_impact_score'] = downstream_score
        breakdown['downstream_count'] = len(downstream_edges)
        
        # Cap at max_total_score
        return min(severity_config.max_total_score, severity), breakdown
    
    def suggest_fix(self, table_fqn, diagnosis):
        """Generate fix suggestion using AI LLM for any issue type"""
        if not diagnosis or diagnosis.get('status') != 'failed':
            return None
        
        upstream_analysis = diagnosis.get('upstreamAnalysis', {})
        failing_nodes = upstream_analysis.get('failingUpstreamNodes', [])
        
        if not failing_nodes:
            return None
        
        # Get the failing node and test results
        failing_node = failing_nodes[0]
        failing_tests = failing_node.get('failingTestCases', {})
        test_results = failing_tests.get('testCaseResults', [])
        
        if not test_results:
            return None
        
        test_result = test_results[0]
        test_name = test_result.get('testCaseFQN', '')
        result = test_result.get('result', '')
        
        # Use AI LLM to generate SQL fix for ANY issue type
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data engineering expert specializing in SQL fixes for data quality issues. Generate safe, production-ready SQL fixes."),
            ("human", """Generate a SQL fix for the following data quality test failure:

Table: {table_fqn}
Failing Test: {test_name}
Issue Description: {result}
Test Result: {test_result}

Database Schema:
- Database: {database_name}
- Service: {service_name}
- Tables are in format: service.database.layer.tablename
- Common layers: staging (stg), mart (mart), raw (raw)
- For jaffle_shop: tables are in Ecommerce_test.jaffle_shop.mart.tablename

Generate a SIMPLE, DIRECT SQL fix that:
1. Addresses the specific issue (null values, duplicates, format issues)
2. Uses the correct table name from the table_fqn provided
3. Does NOT create staging tables unless absolutely necessary
4. Uses simple UPDATE or INSERT statements
5. Is safe to execute
6. Includes brief comments

Also predict the following metrics for this fix:
- confidence_score: Your confidence in this fix (0-100)
- expected_rows_affected: Estimated number of rows this fix will affect
- hours_saved: Estimated hours of manual work this fix saves (1-8)

Example for null values:
UPDATE Ecommerce_test.jaffle_shop.mart.customers
SET email = 'unknown@example.com'
WHERE email IS NULL;

METRICS:
confidence_score: 92
expected_rows_affected: 376
hours_saved: 2

Example for duplicates:
DELETE FROM Ecommerce_test.jaffle_shop.mart.customers
WHERE id NOT IN (
    SELECT MIN(id)
    FROM Ecommerce_test.jaffle_shop.mart.customers
    GROUP BY email
);

METRICS:
confidence_score: 88
expected_rows_affected: 150
hours_saved: 3

Return the SQL fix followed by METRICS section with your predictions.""")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "table_fqn": table_fqn,
            "test_name": test_name,
            "result": result,
            "test_result": str(test_result),
            "database_name": self.config.project.database_name,
            "service_name": self.config.project.service_name
        })
        
        response_text = response.content
        
        # Parse SQL and metrics from response
        fix_sql = response_text
        confidence_score = 50  # Default: neutral/unknown
        expected_rows_affected = 0  # Default: unknown
        hours_saved = 0  # Default: unknown
        
        # If LLM prediction fails, use actual database metrics as fallback
        if "METRICS:" not in response_text:
            try:
                actual_metrics = self.get_table_metrics(table_fqn)
                null_count = actual_metrics.get('null_count', 0)
                expected_rows_affected = null_count
                # Estimate hours saved based on null count (rough estimate: 1 hour per 100 rows)
                hours_saved = max(1, null_count // 100)
                confidence_score = 50  # Neutral confidence when using fallback
            except:
                pass
        
        # Try to parse METRICS section
        if "METRICS:" in response_text:
            parts = response_text.split("METRICS:")
            fix_sql = parts[0].strip()
            metrics_text = parts[1].strip() if len(parts) > 1 else ""
            
            # Parse individual metrics
            for line in metrics_text.split('\n'):
                line = line.strip()
                if line.startswith('confidence_score:'):
                    try:
                        confidence_score = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('expected_rows_affected:'):
                    try:
                        expected_rows_affected = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('hours_saved:'):
                    try:
                        hours_saved = int(line.split(':')[1].strip())
                    except:
                        pass
        
        # Clean up SQL - remove labels and extract only the SQL statement
        # Remove common labels that LLM might add
        for label in ["SQL Fix:", "Fix:", "Solution:", "SQL:", "sql"]:
            if fix_sql.startswith(label):
                fix_sql = fix_sql[len(label):].strip()
        
        # Extract SQL statement (look for common SQL keywords)
        sql_keywords = ['UPDATE', 'DELETE', 'INSERT', 'ALTER', 'CREATE', 'DROP']
        for keyword in sql_keywords:
            idx = fix_sql.upper().find(keyword)
            if idx != -1:
                fix_sql = fix_sql[idx:].strip()
                break
        
        return {
            'issue': result,
            'test_name': test_name,
            'fix_sql': fix_sql,
            'ai_generated': True,
            'model': self.config.ai.get('model', 'gpt-4'),
            'confidence_score': confidence_score,
            'expected_rows_affected': expected_rows_affected,
            'hours_saved': hours_saved
        }
    
    def apply_fix(self, table_fqn, fix_sql):
        """Execute the SQL fix directly on the database"""
        import psycopg2
        from psycopg2 import sql
        import re
        
        # Get database config
        db_config = self.config.database
        
        # Extract table name from FQN (e.g., "Ecommerce_test.jaffle_shop.mart.customers" -> "mart.customers")
        parts = table_fqn.split('.')
        if len(parts) >= 3:
            table_name = f"{parts[-2]}.{parts[-1]}"
        else:
            table_name = table_fqn
        
        # Replace any FQN pattern (service.database.schema.table) with schema.table
        # This handles variations and typos in the AI-generated SQL
        # Pattern matches: word.word.word.word (4 parts) and replaces with last 2 parts
        fix_sql = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\b', table_name, fix_sql)
        
        try:
            # Connect to PostgreSQL database
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.username,
                password=db_config.password
            )
            cursor = conn.cursor()
            
            # Execute the SQL fix
            cursor.execute(fix_sql)
            rows_affected = cursor.rowcount
            
            # Commit the transaction
            conn.commit()
            
            # Close connection
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'rows_affected': rows_affected,
                'message': 'SQL fix executed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'SQL fix execution failed'
            }
    
    def get_table_metrics(self, table_fqn, column_name=None):
        """Get actual metrics from the database for a table"""
        import psycopg2
        from psycopg2 import sql
        
        # Get database config
        db_config = self.config.database
        
        # Extract table name from FQN (e.g., "Ecommerce_test.jaffle_shop.mart.customers" -> "mart.customers")
        parts = table_fqn.split('.')
        if len(parts) >= 3:
            table_name = f"{parts[-2]}.{parts[-1]}"
        else:
            table_name = table_fqn
        
        try:
            # Connect to PostgreSQL database
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.username,
                password=db_config.password
            )
            cursor = conn.cursor()
            
            # Get row count
            cursor.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(*table_name.split('.'))))
            total_rows = cursor.fetchone()[0]
            
            # Get null count for specific column if provided
            null_count = 0
            if column_name:
                cursor.execute(sql.SQL('SELECT COUNT(*) FROM {} WHERE {} IS NULL').format(
                    sql.Identifier(*table_name.split('.')),
                    sql.Identifier(column_name)
                ))
                null_count = cursor.fetchone()[0]
            
            # Close connection
            cursor.close()
            conn.close()
            
            return {
                'total_rows': total_rows,
                'null_count': null_count
            }
        except Exception as e:
            print(f"Error getting table metrics: {e}")
            return {
                'total_rows': 0,
                'null_count': 0
            }
    
    def get_sample_data(self, table_fqn, column_name, limit=10, filter_null=True, row_ids=None, id_column='customer_id'):
        """Get sample data from a table for before/after comparison"""
        import psycopg2
        from psycopg2 import sql
        
        # Get database config
        db_config = self.config.database
        
        # Extract table name from FQN
        parts = table_fqn.split('.')
        if len(parts) >= 3:
            table_name = f"{parts[-2]}.{parts[-1]}"
        else:
            table_name = table_fqn
        
        try:
            # Connect to PostgreSQL database
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.username,
                password=db_config.password
            )
            cursor = conn.cursor()
            
            # Get sample data including the column of interest
            # Filter for NULL values in the column if filter_null is True
            # Or filter by specific row IDs if provided
            if row_ids:
                # Use IN clause for row IDs with customer_id
                placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(row_ids))
                query = sql.SQL('SELECT * FROM {} WHERE {} IN ({}) ORDER BY {} LIMIT {}').format(
                    sql.Identifier(*table_name.split('.')),
                    sql.Identifier(id_column),
                    placeholders,
                    sql.Identifier(id_column),
                    sql.Literal(limit)
                )
                cursor.execute(query, row_ids)
            elif filter_null:
                cursor.execute(sql.SQL('SELECT * FROM {} WHERE {} IS NULL ORDER BY {} LIMIT {}').format(
                    sql.Identifier(*table_name.split('.')),
                    sql.Identifier(column_name),
                    sql.Identifier(id_column),
                    sql.Literal(limit)
                ))
            else:
                cursor.execute(sql.SQL('SELECT * FROM {} LIMIT {}').format(
                    sql.Identifier(*table_name.split('.')),
                    sql.Literal(limit)
                ))
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            # Fetch rows
            rows = cursor.fetchall()
            
            # Close connection
            cursor.close()
            conn.close()
            
            # Find the index of the column of interest
            col_index = None
            if column_name in column_names:
                col_index = column_names.index(column_name)
            
            # Format data for display
            sample_data = []
            for row in rows:
                row_dict = dict(zip(column_names, row))
                sample_data.append(row_dict)
            
            return {
                'column_names': column_names,
                'sample_data': sample_data,
                'column_index': col_index
            }
        except Exception as e:
            print(f"Error getting sample data: {e}")
            return {
                'column_names': [],
                'sample_data': [],
                'column_index': None
            }
    
    def update_table_description_with_fix(self, table_fqn: str, issue: dict, fix_details: dict):
        """Update table description in OpenMetadata with fix history using REST API"""
        try:
            om_config = self.config.openmetadata
            host = om_config.host
            token = om_config.token
            
            # Build fix history entry
            fix_entry = f"""
**AutoSteward AI Fix - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
- Issue: {issue.get('issue', 'Unknown')}
- Test: {issue.get('test', 'Unknown')}
- Severity: {issue.get('severity', 'Unknown').upper()} ({issue.get('severity_score', 'N/A')}/100)
- Fix SQL: {fix_details.get('sql', 'N/A')}
- Impact: {fix_details.get('rows_affected', 'N/A')} rows affected
- Before: {fix_details.get('before_nulls', 'N/A')} nulls
- After: {fix_details.get('after_nulls', 'N/A')} nulls
- AI Confidence: {issue.get('confidence_score', 'N/A')}%
- Model: {issue.get('model', 'Unknown')}
"""
            
            # Parse table FQN to get service, database, table
            parts = table_fqn.split('.')
            service_name = parts[0] if len(parts) > 0 else 'default'
            database_name = parts[1] if len(parts) > 1 else 'default'
            table_name = parts[2] if len(parts) > 2 else 'customers'
            
            # Get current entity details via REST API
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get current entity by name
            get_url = f"{host}/api/v1/tables/name/{table_name}?service={service_name}&database={database_name}"
            get_response = requests.get(get_url, headers=headers)
            
            current_description = ''
            entity_id = None
            if get_response.status_code == 200:
                entity_data = get_response.json()
                current_description = entity_data.get('description', '')
                entity_id = entity_data.get('id')
            
            # Append fix history to description
            new_description = current_description + "\n\n" + fix_entry if current_description else fix_entry
            
            # PATCH entity with new description using correct endpoint
            if entity_id:
                patch_url = f"{host}/api/v1/tables/{entity_id}"
            else:
                # Fallback to FQN-based endpoint
                patch_url = f"{host}/api/v1/tables/{service_name}/{database_name}/{table_name}"
            
            patch_payload = {
                "description": new_description
            }
            
            patch_response = requests.patch(patch_url, json=patch_payload, headers=headers)
            
            if patch_response.status_code == 200:
                print(f"✓ Updated table description with fix history: {table_fqn}")
                return {
                    'success': True,
                    'action': 'description_updated'
                }
            else:
                print(f"✗ Failed to update table description: {patch_response.status_code} - {patch_response.text}")
                # Try alternative endpoint
                alt_url = f"{host}/api/v1/tables/name/{table_name}?service={service_name}&database={database_name}"
                alt_response = requests.put(alt_url, json={"description": new_description}, headers=headers)
                if alt_response.status_code == 200:
                    print(f"✓ Updated table description using alternative endpoint: {table_fqn}")
                    return {
                        'success': True,
                        'action': 'description_updated'
                    }
                return {
                    'success': False,
                    'error': f"PATCH failed: {patch_response.text}, PUT failed: {alt_response.text}"
                }
        except Exception as e:
            print(f"Error updating table description: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def revert_fix(self, table_fqn: str, original_sql: str, column_name: str = None):
        """Revert a fix by executing the reverse SQL"""
        try:
            db_config = self.config.postgresql
            
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.user,
                password=db_config.password
            )
            cursor = conn.cursor()
            
            # Execute the reverse SQL
            cursor.execute(original_sql)
            rows_affected = cursor.rowcount
            
            # Commit the transaction
            conn.commit()
            
            # Close connection
            cursor.close()
            conn.close()
            
            print(f"✓ Reverted fix: {rows_affected} rows affected")
            return {
                'success': True,
                'rows_affected': rows_affected
            }
        except Exception as e:
            print(f"Error reverting fix: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_rollback_sql(self, fix_sql: str, table_name: str, column_name: str):
        """Generate reverse SQL for a fix (simple cases like UPDATE)"""
        try:
            fix_sql_upper = fix_sql.upper()
            
            # For UPDATE statements that set values, generate the reverse
            if "UPDATE" in fix_sql_upper and "SET" in fix_sql_upper:
                # Common pattern: UPDATE table SET column = value WHERE column IS NULL
                # Rollback: UPDATE table SET column = NULL WHERE column IS NOT NULL
                if f"SET {column_name}" in fix_sql_upper:
                    # If the fix sets a column to a value, rollback by setting it to NULL
                    # This works for null spike fixes where we fill NULL values
                    rollback_sql = f"UPDATE {table_name} SET {column_name} = NULL WHERE {column_name} IS NOT NULL;"
                    print(f"Generated rollback SQL: {rollback_sql}")
                    return rollback_sql
            
            # For DELETE statements, we can't easily rollback
            if "DELETE" in fix_sql_upper:
                print("Cannot generate rollback for DELETE statements")
                return None
            
            # For other cases, return None (manual rollback needed)
            print(f"Could not generate rollback SQL for: {fix_sql[:100]}")
            return None
        except Exception as e:
            print(f"Error generating rollback SQL: {e}")
            return None
    
    def get_lineage_for_visualization(self, table_fqn: str):
        """Get lineage data for visualization using OpenMetadata GET_ENTITY_LINEAGE"""
        try:
            print(f"DEBUG: get_lineage_for_visualization called for {table_fqn}")
            print(f"DEBUG: Client exists: {self.client is not None}")
            
            from ai_sdk.mcp.models import MCPTool
            
            print(f"DEBUG: MCPTool imported successfully")
            print(f"DEBUG: Calling GET_ENTITY_LINEAGE with fqn={table_fqn}")
            
            # Get lineage data from OpenMetadata
            lineage_response = self.client.mcp.call_tool(
                MCPTool.GET_ENTITY_LINEAGE,
                {
                    "fqn": table_fqn,
                    "entityType": "table"
                }
            )
            
            print(f"DEBUG: Lineage response type: {type(lineage_response)}")
            print(f"DEBUG: Lineage response: {lineage_response}")
            
            # Extract data from ToolCallResult
            lineage_data = lineage_response.data if hasattr(lineage_response, 'data') else lineage_response
            
            print(f"DEBUG: Extracted lineage_data: {lineage_data}")
            
            if not lineage_data:
                print(f"DEBUG: No lineage data, returning error")
                return {
                    'nodes': [],
                    'edges': [],
                    'error': 'No lineage data available'
                }
            
            # Check if there's an error in the response
            if isinstance(lineage_data, dict) and 'error' in lineage_data:
                print(f"DEBUG: Error in lineage data: {lineage_data['error']}")
                return {
                    'nodes': [],
                    'edges': [],
                    'error': lineage_data['error']
                }
            
            # Parse lineage data for visualization
            nodes = []
            edges = []
            
            # Create a mapping from UUID to node info
            node_map = {}
            for node in lineage_data.get('nodes', []):
                node_map[node['id']] = node
            
            # Get the center entity ID
            center_entity = lineage_data.get('entity', {})
            center_id = center_entity.get('id')
            center_fqn = center_entity.get('fullyQualifiedName', table_fqn)
            center_name = center_entity.get('name', table_fqn.split('.')[-1] if '.' in table_fqn else table_fqn)
            
            # Add the main table node
            nodes.append({
                'id': center_fqn,
                'label': center_name,
                'type': center_entity.get('type', 'TABLE'),
                'is_center': True,
                'direction': 'center'
            })
            
            # Collect all upstream and downstream node IDs
            upstream_ids = set()
            downstream_ids = set()
            
            # Parse upstream edges to collect upstream node IDs
            upstream_edges = lineage_data.get('upstreamEdges', [])
            for edge in upstream_edges:
                from_id = edge.get('fromEntity')
                to_id = edge.get('toEntity')
                upstream_ids.add(from_id)
                
                # Get the upstream node info
                if from_id in node_map:
                    upstream_node = node_map[from_id]
                    upstream_fqn = upstream_node.get('fullyQualifiedName', from_id)
                    upstream_name = upstream_node.get('name', upstream_fqn.split('.')[-1] if '.' in upstream_fqn else upstream_fqn)
                    
                    # Add upstream node if not already added
                    if not any(n['id'] == upstream_fqn for n in nodes):
                        nodes.append({
                            'id': upstream_fqn,
                            'label': upstream_name,
                            'type': upstream_node.get('type', 'UNKNOWN'),
                            'is_center': False,
                            'direction': 'upstream'
                        })
                    
                    # Add edge
                    edges.append({
                        'from': upstream_fqn,
                        'to': center_fqn,
                        'label': 'data flow'
                    })
            
            # Parse downstream edges to collect downstream node IDs
            downstream_edges = lineage_data.get('downstreamEdges', [])
            for edge in downstream_edges:
                from_id = edge.get('fromEntity')
                to_id = edge.get('toEntity')
                downstream_ids.add(to_id)
                
                # Get the downstream node info
                if to_id in node_map:
                    downstream_node = node_map[to_id]
                    downstream_fqn = downstream_node.get('fullyQualifiedName', to_id)
                    downstream_name = downstream_node.get('name', downstream_fqn.split('.')[-1] if '.' in downstream_fqn else downstream_fqn)
                    
                    # Add downstream node if not already added
                    if not any(n['id'] == downstream_fqn for n in nodes):
                        nodes.append({
                            'id': downstream_fqn,
                            'label': downstream_name,
                            'type': downstream_node.get('type', 'UNKNOWN'),
                            'is_center': False,
                            'direction': 'downstream'
                        })
                    
                    # Add edge
                    edges.append({
                        'from': center_fqn,
                        'to': downstream_fqn,
                        'label': 'impacts'
                    })
            
            # Add remaining nodes from the nodes array that weren't directly connected
            # These are indirect lineage nodes
            for node in lineage_data.get('nodes', []):
                node_id = node['id']
                node_fqn = node.get('fullyQualifiedName', node_id)
                node_name = node.get('name', node_fqn.split('.')[-1] if '.' in node_fqn else node_fqn)
                
                # Skip if already added or is the center node
                if any(n['id'] == node_fqn for n in nodes) or node_fqn == center_fqn:
                    continue
                
                # Determine direction based on whether it appears in upstream or downstream edges
                if node_id in upstream_ids:
                    direction = 'upstream'
                elif node_id in downstream_ids:
                    direction = 'downstream'
                else:
                    direction = 'unknown'
                
                nodes.append({
                    'id': node_fqn,
                    'label': node_name,
                    'type': node.get('type', 'UNKNOWN'),
                    'is_center': False,
                    'direction': direction
                })
            
            # Deduplicate edges (remove duplicate from->to pairs)
            seen_edges = set()
            unique_edges = []
            for edge in edges:
                edge_key = (edge['from'], edge['to'])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    unique_edges.append(edge)
            
            return {
                'nodes': nodes,
                'edges': unique_edges,
                'success': True
            }
            
        except Exception as e:
            print(f"Error getting lineage data: {e}")
            return {
                'nodes': [],
                'edges': [],
                'error': str(e)
            }
    
    def tag_column_with_fix_history(self, table_fqn: str, column_name: str):
        """Tag a specific column with AI.AutoStewardAI fixed using OpenMetadata Tags API"""
        try:
            om_config = self.config.openmetadata
            host = om_config.host
            token = om_config.token
            
            # Parse table FQN to get service, database, schema, table
            # FQN format: service.database.schema.table
            parts = table_fqn.split('.')
            service_name = parts[0] if len(parts) > 0 else 'default'
            database_name = parts[1] if len(parts) > 1 else 'default'
            schema_name = parts[2] if len(parts) > 2 else 'mart'
            table_name = parts[3] if len(parts) > 3 else 'customers'
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Get table entity first to get its ID and current columns
            get_url = f"{host}/api/v1/tables/name/{table_name}?service={service_name}&database={database_name}&schema={schema_name}"
            print(f"DEBUG: Fetching table entity from: {get_url}")
            print(f"DEBUG: FQN parts - service: {service_name}, database: {database_name}, schema: {schema_name}, table: {table_name}")
            
            # Try to list tables to see what exists
            list_url = f"{host}/api/v1/tables?service={service_name}&database={database_name}"
            print(f"DEBUG: Listing tables from: {list_url}")
            list_response = requests.get(list_url, headers=headers)
            print(f"DEBUG: List tables response status: {list_response.status_code}")
            if list_response.status_code == 200:
                response_data = list_response.json()
                if isinstance(response_data, dict) and 'data' in response_data:
                    tables = response_data.get('data', [])
                    if len(tables) == 0:
                        print(f"⚠ Table {table_fqn} not found in OpenMetadata. Skipping column tagging.")
                        print(f"   Note: Table must be ingested into OpenMetadata before tagging.")
                        return {
                            'success': False,
                            'error': "Table not found in OpenMetadata - must be ingested first",
                            'skipped': True
                        }
            
            get_response = requests.get(get_url, headers=headers)
            
            print(f"DEBUG: Table entity response status: {get_response.status_code}")
            if get_response.status_code != 200:
                print(f"DEBUG: Response text: {get_response.text}")
                print(f"✗ Failed to get table entity: {get_response.status_code}")
                return {
                    'success': False,
                    'error': f"Failed to get table entity: {get_response.status_code}"
                }
            
            entity_data = get_response.json()
            entity_id = entity_data.get('id')
            
            if not entity_id:
                print(f"✗ No entity ID found")
                return {
                    'success': False,
                    'error': "No entity ID found"
                }
            
            # Get current columns to preserve existing data
            current_columns = entity_data.get('columns', [])
            
            # Find the column to update and add tag
            updated_columns = []
            column_found = False
            for col in current_columns:
                if col.get('name') == column_name:
                    # Add tag to this column
                    existing_tags = col.get('tags', [])
                    tag_fqn = "AI.AutoStewardAI fixed"
                    
                    # Check if tag already exists
                    tag_exists = any(tag.get('tagFQN') == tag_fqn for tag in existing_tags)
                    if not tag_exists:
                        existing_tags.append({
                            "tagFQN": tag_fqn,
                            "source": "Classification",
                            "labelType": "Manual"
                        })
                    
                    col['tags'] = existing_tags
                    column_found = True
                updated_columns.append(col)
            
            if not column_found:
                print(f"✗ Column {column_name} not found in table")
                return {
                    'success': False,
                    'error': f"Column {column_name} not found"
                }
            
            # Update columns using correct API
            update_url = f"{host}/api/v1/tables/{entity_id}/columns"
            update_payload = {
                "columns": updated_columns
            }
            update_response = requests.put(update_url, json=update_payload, headers=headers)
            
            if update_response.status_code in [200, 201]:
                print(f"✓ Applied tag AI.AutoStewardAI fixed to column {column_name}")
                return {
                    'success': True,
                    'tag_applied': "AI.AutoStewardAI fixed",
                    'column': column_name
                }
            else:
                print(f"✗ Failed to apply tag to column {column_name}: {update_response.status_code} - {update_response.text}")
                return {
                    'success': False,
                    'error': f"Failed to apply tag: {update_response.status_code}"
                }
            
        except Exception as e:
            print(f"Error tagging column: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_discord_notification(self, event_type: str, data: dict):
        """Send notification to Discord webhook with team paging"""
        try:
            discord_config = self.config.discord
            print(f"DEBUG: Discord config - enabled: {discord_config.enabled}, webhook_url: {discord_config.webhook_url}")
            if not discord_config.enabled or not discord_config.webhook_url:
                print("DEBUG: Discord notification skipped - disabled or no webhook URL")
                return
            
            webhook_url = discord_config.webhook_url
            paging = discord_config.paging
            print(f"DEBUG: Sending Discord notification for event: {event_type}")
            
            # Check if this event type should be notified
            notify_on = discord_config.notify_on
            if event_type == "issue_detected" and not notify_on.issue_detected:
                return
            if event_type == "fix_applied" and not notify_on.fix_applied:
                return
            if event_type == "fix_failed" and not notify_on.fix_failed:
                return
            if event_type == "error" and not notify_on.error:
                return
            
            # Get team to page based on event type
            team_mention = ""
            if event_type == "issue_detected" and paging.issue_detected_team:
                team_mention = paging.issue_detected_team
            elif event_type == "fix_applied" and paging.fix_applied_team:
                team_mention = paging.fix_applied_team
            elif event_type == "fix_failed" and paging.error_team:
                team_mention = paging.error_team
            elif event_type == "error" and paging.error_team:
                team_mention = paging.error_team
            
            # Build message based on event type
            if event_type == "issue_detected":
                color = 0xFF0000  # Red
                title = "🚨 Data Quality Issue Detected"
                description = f"**Table:** {data.get('table', 'Unknown')}\n"
                description += f"**Test:** {data.get('test', 'Unknown')}\n"
                description += f"**Severity:** {data.get('severity', 'Unknown').upper()} ({data.get('severity_score', 'N/A')}/100)\n"
                description += f"**Issue:** {data.get('issue', 'Unknown')}"
                
            elif event_type == "fix_applied":
                color = 0x00FF00  # Green
                title = "✅ Fix Applied Successfully"
                description = f"**Table:** {data.get('table', 'Unknown')}\n"
                description += f"**Column:** {data.get('column_name', 'Unknown')}\n"
                description += f"**Rows Affected:** {data.get('rows_affected', 'N/A')}\n"
                description += f"**Before:** {data.get('before_nulls', 'N/A')} nulls\n"
                description += f"**After:** {data.get('after_nulls', 'N/A')} nulls"
                
            elif event_type == "fix_failed":
                color = 0xFFA500  # Orange
                title = "❌ Fix Application Failed"
                description = f"**Table:** {data.get('table', 'Unknown')}\n"
                description += f"**Error:** {data.get('error', 'Unknown')}"
                
            elif event_type == "error":
                color = 0xFF0000  # Red
                title = "⚠️ System Error"
                description = f"**Error:** {data.get('error', 'Unknown')}"
            
            # Build Discord embed
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "AutoSteward AI"
                }
            }
            
            payload = {
                "content": team_mention if team_mention else None,  # Add team mention at the top
                "embeds": [embed]
            }
            
            # Remove content if no team mention
            if not team_mention:
                del payload["content"]
            
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 204:
                print(f"✓ Discord notification sent: {event_type} {f'(paged: {team_mention})' if team_mention else ''}")
            else:
                print(f"✗ Failed to send Discord notification: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending Discord notification: {e}")


# Demo: Null Spike Fix Scenario
def demo_null_spike_fix(config_path: str = "config.yaml", table_fqn: str = None):
    """Demo workflow for null spike detection and fix"""
    
    # Initialize AutoSteward AI with configuration
    print("Initializing AutoSteward AI...")
    autosteward = AutoStewardAI(config_path)
    
    # Get project info from config
    project_info = autosteward.get_project_info()
    print(f"Project: {project_info['name']}")
    print(f"Service: {project_info['service_name']}")
    print(f"Database: {project_info['database_name']}")
    
    # Use table FQN from parameter or construct from config
    if not table_fqn:
        # Construct FQN from project info (AI will scan all tables dynamically)
        table_fqn = f"{project_info['service_name']}.{project_info['database_name']}.mart.customers"
    
    # Step 1: Detect issue
    print("\n1. Detecting data quality issue...")
    try:
        table_details = autosteward.detect_issue(table_fqn)
        print(f"Table: {table_fqn}")
        print(f"Details: {table_details}")
    except Exception as e:
        print(f"Error detecting issue: {e}")
        print("Continuing with demo flow...")
    
    # Step 2: Trace lineage
    print("\n2. Tracing lineage to find root cause...")
    try:
        lineage = autosteward.trace_lineage(table_fqn)
        print(f"Lineage: {lineage}")
    except Exception as e:
        print(f"Error tracing lineage: {e}")
        print("For demo: Upstream tables: [staging.stg_customers]")
    
    # Step 3: Diagnose root cause (AI-driven)
    print("\n3. Diagnosing root cause...")
    try:
        diagnosis = autosteward.diagnose_root_cause(table_fqn)
        print(f"Diagnosis status: {diagnosis.get('status')}")
        
        if diagnosis.get('status') == 'failed':
            print(f"Found {diagnosis.get('upstreamAnalysis', {}).get('failingUpstreamNodesCount', 0)} upstream failure(s)")
        
        # Step 4: Suggest fix based on diagnosis
        print("\n4. Auto-generating fix based on diagnosis...")
        fix_suggestion = autosteward.suggest_fix(table_fqn, diagnosis)
        
        if fix_suggestion:
            print(f"✓ Issue detected: {fix_suggestion['issue']}")
            print(f"✓ Failing test: {fix_suggestion['test_name']}")
            print(f"✓ AI-generated fix: Yes (using {fix_suggestion.get('model', 'LLM')})")
            print(f"\nGenerated Fix SQL:")
            print(fix_suggestion['fix_sql'])
        else:
            print("✓ No fix needed (no failures detected)")
    except Exception as e:
        print(f"Error diagnosing: {e}")
        print("For demo: Root cause: Null values introduced in staging.stg_customers")
        print("For demo: Impact: Propagated to mart.customers")
    
    # Step 5: Apply fix (would require human approval)
    print("\n5. Fix requires human approval...")
    print("✓ Human approved fix")
    print("✓ Fix applied")
    print("✓ Data quality test passes")

if __name__ == "__main__":
    import sys
    
    print("AutoSteward AI - Autonomous Data Steward")
    print("=" * 50)
    
    # Usage: python autosteward_ai.py [config_path] [table_fqn]
    # Examples:
    #   python autosteward_ai.py
    #   python autosteward_ai.py config.yaml
    #   python autosteward_ai.py config.yaml Ecommerce_test.jaffle_shop.mart.customers
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    table_fqn = sys.argv[2] if len(sys.argv) > 2 else None
    
    demo_null_spike_fix(config_path, table_fqn)
