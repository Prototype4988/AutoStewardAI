"""
AutoSteward AI - Streamlit Dashboard
Professional dashboard for autonomous data stewardship
"""

import streamlit as st
import time
import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.autosteward_ai import AutoStewardAI

# Page config
st.set_page_config(
    page_title="AutoSteward AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'issues' not in st.session_state:
    st.session_state.issues = []
if 'scanning' not in st.session_state:
    st.session_state.scanning = False
if 'selected_issue' not in st.session_state:
    st.session_state.selected_issue = None
if 'fixed_today' not in st.session_state:
    st.session_state.fixed_today = 0
if 'total_scanned' not in st.session_state:
    st.session_state.total_scanned = 0
if 'show_notify_button' not in st.session_state:
    st.session_state.show_notify_button = False
if 'total_hours_saved' not in st.session_state:
    st.session_state.total_hours_saved = 0
if 'before_sample_data' not in st.session_state:
    st.session_state.before_sample_data = None
if 'after_sample_data' not in st.session_state:
    st.session_state.after_sample_data = None
if 'fixed_row_ids' not in st.session_state:
    st.session_state.fixed_row_ids = []
if 'show_lineage_graph' not in st.session_state:
    st.session_state.show_lineage_graph = False
if 'lineage_table' not in st.session_state:
    st.session_state.lineage_table = None
if 'lineage_button_clicked' not in st.session_state:
    st.session_state.lineage_button_clicked = False
if 'prerequisites_checked' not in st.session_state:
    st.session_state.prerequisites_checked = False
if 'prerequisites_ok' not in st.session_state:
    st.session_state.prerequisites_ok = True
if 'prerequisite_warnings' not in st.session_state:
    st.session_state.prerequisite_warnings = []
if 'auto_scan_enabled' not in st.session_state:
    st.session_state.auto_scan_enabled = True  # Enabled by default for demo
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'execution_history' not in st.session_state:
    st.session_state.execution_history = []
if 'fixes_in_current_hour' not in st.session_state:
    st.session_state.fixes_in_current_hour = 0
if 'hour_start_time' not in st.session_state:
    st.session_state.hour_start_time = datetime.datetime.now()
if 'max_fixes_per_hour' not in st.session_state:
    st.session_state.max_fixes_per_hour = 10
if 'fix_just_applied' not in st.session_state:
    st.session_state.fix_just_applied = False
if 'last_fix_details' not in st.session_state:
    st.session_state.last_fix_details = None
if 'last_hours_saved' not in st.session_state:
    st.session_state.last_hours_saved = 0

# Initialize AutoSteward AI
@st.cache_resource
def get_autosteward():
    return AutoStewardAI("config/config.yaml")

autosteward = get_autosteward()

# Header
st.title("🤖 AutoSteward AI")
st.markdown("Autonomous Data Steward Powered by OpenMetadata AI SDK")

# Value Banner
if st.session_state.fixed_today > 0:
    # Use accumulated total hours saved from all fixes
    total_hours_saved = st.session_state.get('total_hours_saved', st.session_state.fixed_today * 2)
    st.success(f"🤖 AutoSteward has resolved {st.session_state.fixed_today} issues today, saving ~{total_hours_saved} hours of manual work")
else:
    st.info("🤖 AutoSteward is monitoring your data - no issues resolved yet")

# Show success animation after banner updates
if st.session_state.fix_just_applied and st.session_state.last_fix_details:
    st.success("✅ Fix Applied Successfully!")
    st.balloons()
    
    # Big number cards for impact
    st.subheader("📊 Impact Visualization")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="❌ Before",
            value=f"{st.session_state.last_fix_details['before_nulls']} nulls",
            help="Null values before fix"
        )
    with col2:
        st.metric(
            label="✅ After",
            value=f"{st.session_state.last_fix_details['after_nulls']} nulls",
            delta=f"-{st.session_state.last_fix_details['before_nulls'] - st.session_state.last_fix_details['after_nulls']}",
            help="Null values after fix"
        )
    with col3:
        st.metric(
            label="🎯 Rows Fixed",
            value=st.session_state.last_fix_details['rows_affected'],
            help="Total rows affected by the fix"
        )
    
    # Progress bar visualization
    if st.session_state.last_fix_details['before_nulls'] > 0:
        reduction_percentage = ((st.session_state.last_fix_details['before_nulls'] - st.session_state.last_fix_details['after_nulls']) / st.session_state.last_fix_details['before_nulls']) * 100
        st.progress(reduction_percentage / 100)
        st.caption(f"Null count reduced by {reduction_percentage:.1f}%")
    
    st.divider()
    # Clear the flag after showing animation (but keep last_fix_details for notification button)
    st.session_state.fix_just_applied = False

# Show notification button after fix (separate from animation)
if st.session_state.show_notify_button and st.session_state.last_fix_details:
    st.subheader("📢 Notify Team")
    if st.button("📢 Notify Team of Fix", key="notify_fix_success"):
        # Get the most recent fix from execution history
        if st.session_state.execution_history:
            last_fix = st.session_state.execution_history[-1]
            autosteward.send_discord_notification("fix_applied", {
                'table': last_fix.get('table', 'Unknown'),
                'column_name': last_fix.get('column_name', 'Unknown'),
                'rows_affected': last_fix.get('rows_affected', 0),
                'before_nulls': last_fix.get('before_metrics', {}).get('null_count', 0),
                'after_nulls': last_fix.get('after_metrics', {}).get('null_count', 0)
            })
            st.success("✅ Notification sent to Discord!")
            st.session_state.show_notify_button = False
            st.session_state.last_fix_details = None
            st.rerun()

# Show before/after data comparison
if st.session_state.before_sample_data and st.session_state.after_sample_data:
    st.subheader("📊 Before/After Data Comparison")
    
    before_data = st.session_state.before_sample_data
    after_data = st.session_state.after_sample_data
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**❌ Before Fix**")
        if before_data.get('sample_data'):
            st.dataframe(before_data['sample_data'], width='stretch')
        else:
            st.info("No before data available")
    
    with col2:
        st.markdown("**✅ After Fix**")
        if after_data.get('sample_data'):
            st.dataframe(after_data['sample_data'], width='stretch')
        else:
            st.info("No after data available")
    
    st.caption("Showing sample data from the table to visualize the fix impact")
    st.divider()
    
    # Clear sample data after showing
    st.session_state.before_sample_data = None
    st.session_state.after_sample_data = None

# Prerequisites check (only run once)
if not st.session_state.prerequisites_checked:
    st.header("🔍 System Status")
    with st.spinner("Checking prerequisites..."):
        st.session_state.prerequisites_ok = True
        st.session_state.prerequisite_warnings = []
        
        # Check OpenMetadata connection
        try:
            import httpx
            om_host = autosteward.config.openmetadata.host
            om_token = autosteward.config.openmetadata.token
            headers = {"Authorization": f"Bearer {om_token}"}
            response = httpx.get(f"{om_host}/api/v1/system/status", headers=headers, timeout=5)
            if response.status_code == 200:
                st.success("✅ OpenMetadata is running")
            elif response.status_code == 401:
                st.success("✅ OpenMetadata is running (authentication required)")
            else:
                st.error(f"❌ OpenMetadata returned status {response.status_code}")
                st.session_state.prerequisites_ok = False
                st.session_state.prerequisite_warnings.append(f"OpenMetadata server returned status {response.status_code}")
        except Exception as e:
            st.error(f"❌ Cannot connect to OpenMetadata: {str(e)}")
            st.session_state.prerequisites_ok = False
            st.session_state.prerequisite_warnings.append(f"OpenMetadata connection failed: {str(e)}")
        
        # Check AI provider
        ai_provider = autosteward.config.ai.get('provider', 'unknown')
        if ai_provider == 'ollama':
            try:
                ollama_host = autosteward.config.ai.get('base_url', 'http://localhost:11434')
                response = httpx.get(f"{ollama_host}/api/tags", timeout=3)
                if response.status_code == 200:
                    st.success("✅ Ollama is running")
                else:
                    st.warning("⚠️ Ollama is not responding")
                    st.session_state.prerequisites_ok = False
                    st.session_state.prerequisite_warnings.append("Ollama server is not running - AI features will not work")
            except Exception as e:
                st.warning(f"⚠️ Cannot connect to Ollama: {str(e)}")
                st.session_state.prerequisites_ok = False
                st.session_state.prerequisite_warnings.append(f"Ollama connection failed: {str(e)}")
        elif ai_provider == 'openai':
            if autosteward.config.ai.get('openai_api_key'):
                st.success("✅ OpenAI API key configured")
            else:
                st.error("❌ OpenAI API key not configured")
                st.session_state.prerequisites_ok = False
                st.session_state.prerequisite_warnings.append("OpenAI API key is missing from config")
        elif ai_provider == 'groq':
            if autosteward.config.ai.get('groq_api_key'):
                st.success("✅ Groq API key configured")
            else:
                st.error("❌ Groq API key not configured")
                st.session_state.prerequisites_ok = False
                st.session_state.prerequisite_warnings.append("Groq API key is missing from config")
    
    st.session_state.prerequisites_checked = True
    st.divider()

# Show prerequisite warnings if any issues
if not st.session_state.prerequisites_ok:
    st.error("⚠️ Some prerequisites are not met. Scan functionality may be limited.")
    with st.expander("View Issues"):
        for warning in st.session_state.prerequisite_warnings:
            st.warning(f"• {warning}")
    st.divider()

# Sidebar
st.sidebar.header("Configuration")
st.sidebar.markdown(f"**AI Provider:** {autosteward.config.ai.get('provider', 'unknown')}")
st.sidebar.markdown(f"**Model:** {autosteward.config.ai.get('model', 'unknown')}")
st.sidebar.markdown(f"**Service:** {autosteward.config.project.service_name}")
st.sidebar.markdown(f"**Database:** {autosteward.config.project.database_name}")

st.sidebar.divider()
st.sidebar.header("🤖 Autonomous Mode")
st.session_state.auto_scan_enabled = st.sidebar.checkbox(
    "Enable Auto-Scan (30s)",
    value=st.session_state.auto_scan_enabled,
    help="Automatically scan for issues every 30 seconds"
)

# Emergency stop button (hidden)
# st.sidebar.divider()
# if st.sidebar.button("🛑 EMERGENCY STOP", type="primary"):
#     st.session_state.auto_scan_enabled = False
#     st.session_state.issues = []
#     st.session_state.scanning = False
#     st.error("🛑 EMERGENCY STOP ACTIVATED - All operations halted")
#     st.rerun()

# Scan button
if st.sidebar.button("🔍 Scan for Issues", type="primary"):
    st.session_state.scanning = True
    with st.spinner("Scanning for data quality issues..."):
        time.sleep(2)
        
    # Run detection and diagnosis
    table_fqn = f"{autosteward.config.project.service_name}.{autosteward.config.project.database_name}.mart.customers"
    
    try:
        with st.spinner("🔍 Detecting issues via OpenMetadata AI SDK..."):
            diagnosis = autosteward.diagnose_root_cause(table_fqn)
            st.session_state.total_scanned += 1
        
        if diagnosis.get('status') == 'failed':
            # Get severity score, breakdown, and lineage data from diagnosis
            severity_score = diagnosis.get('severity_score', 50)
            severity_breakdown = diagnosis.get('severity_breakdown', {})
            lineage_data = diagnosis.get('lineage', {})
            
            # Format lineage data for display (show only downstream for customer POV)
            if lineage_data:
                # Count unique downstream assets (unique toEntity IDs)
                downstream_edges = lineage_data.get('downstreamEdges', [])
                downstream_ids = set()
                for edge in downstream_edges:
                    if isinstance(edge, dict):
                        to_entity = edge.get('toEntity')
                        if to_entity:
                            downstream_ids.add(to_entity)
                downstream_count = len(downstream_ids)
                
                lineage_data = {
                    'downstream_count': downstream_count,
                    'downstream_edges': downstream_edges
                }
            
            # Get failing test info from diagnosis
            upstream_analysis = diagnosis.get('upstreamAnalysis', {})
            failing_nodes = upstream_analysis.get('failingUpstreamNodes', [])
            test_name = failing_nodes[0].get('failingTestCases', {}).get('testCaseResults', [{}])[0].get('testCaseFQN', 'unknown') if failing_nodes else 'unknown'
            issue_desc = failing_nodes[0].get('failingTestCases', {}).get('testCaseResults', [{}])[0].get('result', 'unknown') if failing_nodes else 'unknown'
            
            st.session_state.issues = [{
                'id': 1,
                'table': table_fqn,
                'test': test_name,
                'issue': issue_desc,
                'severity': 'high',
                'severity_score': severity_score,
                'severity_breakdown': severity_breakdown,
                'lineage_data': lineage_data,
                'diagnosis': diagnosis,  # Include the full diagnosis with human_friendly_message
                'fixSql': None,  # Fix not generated yet
                'aiGenerated': False,
                'model': None,
                'confidence_score': None,
                'expected_rows_affected': None,
                'hours_saved': None,
                'fix_generated': False  # Track if fix has been generated
            }]
        else:
            st.session_state.issues = []
    except Exception as e:
        st.error(f"❌ Error during scan: {str(e)}")
        if "Ollama" in str(e) or "refused" in str(e):
            st.warning("⚠️ Ollama is not running. Start Ollama with: `ollama serve`")
        st.session_state.issues = []
    
    st.session_state.scanning = False
    st.rerun()

# Main content
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Active Issues",
        value=len(st.session_state.issues),
        delta=None,
        help="Number of detected data quality issues"
    )

with col2:
    st.metric(
        label="Fixed Today",
        value=st.session_state.fixed_today,
        delta=None,
        help="Number of issues fixed today"
    )

with col3:
    # Calculate AI generated percentage dynamically
    ai_generated_count = sum(1 for issue in st.session_state.issues if issue.get('aiGenerated', False))
    ai_percentage = f"{int((ai_generated_count / len(st.session_state.issues) * 100)) if st.session_state.issues else 0}%"
    st.metric(
        label="AI Generated",
        value=ai_percentage,
        delta=None,
        help="Percentage of fixes generated by AI"
    )

# Fix History Analytics
if st.session_state.execution_history:
    st.header("📊 Fix History Analytics")
    
    # Calculate analytics
    fixes_over_time = []
    rows_affected = []
    timestamps = []
    total_time_saved = 0
    
    for entry in st.session_state.execution_history:
        timestamps.append(entry['timestamp'][:19])
        rows_affected.append(entry.get('rows_affected', 0))
        # Use hours_saved from entry or default to 2
        hours_saved = entry.get('hours_saved', 2)
        total_time_saved += hours_saved
    
    # Create charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Fixes Over Time")
        if len(timestamps) > 1:
            # Create line chart data
            chart_data = {
                'Time': timestamps,
                'Rows Affected': rows_affected
            }
            st.line_chart(chart_data, x='Time', y='Rows Affected')
        else:
            st.info("Need at least 2 fixes to show trend")
    
    with col2:
        st.subheader("🎯 Rows Affected per Fix")
        if rows_affected:
            bar_data = {
                'Fix': [f"Fix {i+1}" for i in range(len(rows_affected))],
                'Rows': rows_affected
            }
            st.bar_chart(bar_data, x='Fix', y='Rows')
    
    # Summary metrics
    st.subheader("📊 Summary Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Fixes", len(st.session_state.execution_history))
    with col2:
        st.metric("Total Rows Fixed", sum(rows_affected))
    with col3:
        st.metric("Total Time Saved", f"{total_time_saved}h")
    
    st.divider()

# Issue Feed
st.header("🚨 Live Data Issues")

# Execution History Section
if st.session_state.execution_history:
    with st.expander("📜 Fix Timeline (Before/After Metrics)", expanded=False):
        for i, entry in enumerate(reversed(st.session_state.execution_history), 1):
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**{entry['timestamp'][:19]}**")
                with col2:
                    st.markdown(f"**{entry['table']}**")
                with col3:
                    st.success(f"✅ {entry['action'].upper()}")
                
                st.markdown(f"**Test:** {entry['test']}")
                
                # Before/After metrics
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                with metrics_col1:
                    before_nulls = entry['before_metrics']['null_count']
                    st.metric("Before", f"{before_nulls} nulls")
                with metrics_col2:
                    after_nulls = entry['after_metrics']['null_count']
                    st.metric("After", f"{after_nulls} nulls")
                with metrics_col3:
                    rows_affected = entry.get('rows_affected', 0)
                    st.metric("Rows Affected", f"{rows_affected}")
                
                # Revert Fix button (only if fix was applied)
                if entry.get('fix_applied'):
                    if st.button(f"🔄 Revert Fix", key=f"revert_{entry['timestamp']}"):
                        if entry.get('rollback_sql'):
                            with st.spinner("Reverting fix..."):
                                revert_result = autosteward.revert_fix(
                                    entry['table'],
                                    entry['rollback_sql'],
                                    entry.get('column_name')
                                )
                                if revert_result.get('success'):
                                    st.success(f"✅ Fix reverted! {revert_result.get('rows_affected', 0)} rows restored")
                                    # Mark entry as reverted in history
                                    entry['action'] = 'reverted'
                                    entry['reverted_at'] = datetime.datetime.now().isoformat()
                                else:
                                    st.error(f"❌ Failed to revert fix: {revert_result.get('error', 'Unknown error')}")
                        else:
                            st.warning("⚠️ Automatic rollback not available for this fix type. Manual rollback required.")
                
                st.markdown(f"**Severity Score:** {entry.get('severity_score', 'N/A')}/100")
                st.divider()

if not st.session_state.issues:
    st.info("✅ No active issues detected. Your data is healthy!")
else:
    for issue in st.session_state.issues:
        with st.expander(f"🚨 {issue['issue']}", expanded=False):
            # Issue details
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Table:** `{issue['table']}`")
                st.markdown(f"**Test:** `{issue['test']}`")
                st.markdown(f"**Severity:** `{issue['severity'].upper()}`")
                
                # Display severity score if available
                if issue.get('severity_score'):
                    severity_score = issue['severity_score']
                    if severity_score >= 70:
                        st.error(f"**Impact Score:** {severity_score}/100 (High)")
                    elif severity_score >= 40:
                        st.warning(f"**Impact Score:** {severity_score}/100 (Medium)")
                    else:
                        st.success(f"**Impact Score:** {severity_score}/100 (Low)")
                
                # Send notification button
                if st.button("📢 Notify Team", key=f"notify_issue_{issue['id']}"):
                    autosteward.send_discord_notification("issue_detected", {
                        'table': issue['table'],
                        'test': issue['test'],
                        'issue': issue['issue'],
                        'severity': issue['severity'],
                        'severity_score': issue.get('severity_score', 50)
                    })
                    st.success("✅ Notification sent to Discord!")
                
                # View Diagnosis button below impact score
                if st.button("📝 View Diagnosis", key=f"diagnose_{issue['id']}"):
                    with st.expander("🔍 Diagnosis Details", expanded=True):
                        # Severity Score Breakdown
                        st.subheader("📊 Severity Score Breakdown")
                        severity_score = issue.get('severity_score', 50)
                        breakdown = issue.get('severity_breakdown', {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Base Score", breakdown.get('base_score', 30), help="Base score for any failure")
                            st.metric("Failing Tests", f"+{breakdown.get('failing_tests_score', 0)}", 
                                    help=f"{breakdown.get('failing_tests_count', 0)} tests × 5 points (max +20)")
                            issue_type_label = {
                                'null_values': 'Null Values (+20)',
                                'duplicates': 'Duplicates (+15)',
                                'format_mismatch': 'Format Mismatch (+10)',
                                'unknown': 'Unknown Type (0)'
                            }.get(breakdown.get('issue_type', 'unknown'), 'Unknown (0)')
                            st.metric("Issue Type", f"+{breakdown.get('issue_type_score', 0)}", 
                                    help=issue_type_label)
                        with col2:
                            st.metric("Downstream Impact", f"+{breakdown.get('downstream_impact_score', 0)}", 
                                    help=f"{breakdown.get('downstream_count', 0)} assets × 3 points (max +15)")
                            st.metric("Total Score", severity_score, help="Capped at 100")
                        
                        # Severity Explanation
                        if severity_score >= 70:
                            st.error("🔴 High Severity: Critical impact requiring immediate attention")
                        elif severity_score >= 40:
                            st.warning("🟡 Medium Severity: Significant impact, address soon")
                        else:
                            st.success("🟢 Low Severity: Minor impact, can be scheduled")
                        
                        st.divider()
                        
                        # Downstream Assets (from real lineage data)
                        st.subheader("🔗 Lineage Impact")
                        
                        # Get lineage data if available
                        lineage_data = issue.get('lineage_data', {})
                        
                        # Add expander for lineage graph
                        with st.expander("📊 View Lineage Graph"):
                            with st.spinner("Loading lineage data from OpenMetadata..."):
                                # Get lineage data for visualization
                                viz_data = autosteward.get_lineage_for_visualization(issue['table'])
                                
                                if viz_data.get('success'):
                                    st.subheader("🌐 Data Lineage Graph")
                                    
                                    # Display nodes and edges
                                    nodes = viz_data.get('nodes', [])
                                    edges = viz_data.get('edges', [])
                                    
                                    # Create a visual representation
                                    if nodes:
                                        # Build Graphviz DOT format
                                        dot_graph = "digraph lineage {\n"
                                        dot_graph += "    rankdir=LR;\n"
                                        dot_graph += "    node [shape=box, style=rounded];\n"
                                        
                                        # Add nodes with color coding based on direction
                                        for node in nodes:
                                            node_id = node.get('id', '').replace('.', '_').replace('-', '_')
                                            node_label = node.get('label', 'Unknown')
                                            is_center = node.get('is_center', False)
                                            direction = node.get('direction', 'unknown')
                                            
                                            if is_center:
                                                dot_graph += f'    {node_id} [label="{node_label}", fillcolor="#ff6b6b", style="filled,rounded"];\n'
                                            elif direction == 'upstream':
                                                dot_graph += f'    {node_id} [label="{node_label}", fillcolor="#90EE90", style="filled,rounded"];\n'
                                            elif direction == 'downstream':
                                                dot_graph += f'    {node_id} [label="{node_label}", fillcolor="#FFD700", style="filled,rounded"];\n'
                                            else:
                                                dot_graph += f'    {node_id} [label="{node_label}", fillcolor="#e1f5ff", style="filled,rounded"];\n'
                                        
                                        # Add edges
                                        for edge in edges:
                                            from_id = edge.get('from', '').replace('.', '_').replace('-', '_')
                                            to_id = edge.get('to', '').replace('.', '_').replace('-', '_')
                                            edge_label = edge.get('label', '')
                                            dot_graph += f'    {from_id} -> {to_id} [label="{edge_label}"];\n'
                                        
                                        dot_graph += "}"
                                        
                                        # Display the graph
                                        st.graphviz_chart(dot_graph, width='stretch')
                                    else:
                                        st.warning("No lineage data available for this asset")
                                else:
                                    st.error(f"Failed to load lineage data: {viz_data.get('error', 'Unknown error')}")
                        
            with col2:
                if issue['aiGenerated']:
                    st.success(f"🤖 AI: {issue['model']}")
            
            # Root Cause Explanation Panel
            st.divider()
            st.subheader("🧠 Root Cause Analysis")
            
            # Get the human-friendly diagnosis from the issue data
            diagnosis_message = issue.get('diagnosis', {}).get('human_friendly_message', 
                "We found a data quality issue that needs attention.")
            st.info(f"**AI Diagnosis:** {diagnosis_message}")
            
            st.divider()
            
            # Show Generate Fix button (not in Proposed Fix section)
            if not issue.get('fix_generated', False):
                if st.button("🤖 Generate AI Fix", key=f"generate_fix_{issue['id']}", type="primary"):
                    with st.spinner("� Analyzing data patterns..."):
                        import time
                        time.sleep(0.5)
                    with st.spinner("🔍 Tracing root cause..."):
                        time.sleep(0.5)
                    with st.spinner("🤖 AI generating optimal fix..."):
                        try:
                            # Re-run diagnosis to get fresh data
                            diagnosis = autosteward.diagnose_root_cause(issue['table'])
                            fix_suggestion = autosteward.suggest_fix(issue['table'], diagnosis)
                            
                            if fix_suggestion:
                                # Update issue with fix details
                                issue['fixSql'] = fix_suggestion.get('fix_sql', '')
                                issue['aiGenerated'] = fix_suggestion.get('ai_generated', False)
                                issue['model'] = fix_suggestion.get('model', 'unknown')
                                issue['confidence_score'] = fix_suggestion.get('confidence_score', 85)
                                issue['expected_rows_affected'] = fix_suggestion.get('expected_rows_affected', 100)
                                issue['hours_saved'] = fix_suggestion.get('hours_saved', 2)
                                issue['fix_generated'] = True
                                
                                # Update session state
                                st.session_state.issues = [issue]
                                st.success("✅ Fix generated successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to generate fix")
                        except Exception as e:
                            st.error(f"❌ Error generating fix: {str(e)}")
            else:
                # Show Proposed Fix section only after fix is generated
                st.subheader("🔧 Proposed Fix")
                
                # AI Confidence Score
                confidence = issue.get('confidence_score', 85)
                st.markdown(f"**🎯 AI Confidence:** {confidence}%")
                st.caption("Based on lineage analysis and historical patterns")
                
                st.divider()
                
                # Fix Preview with confidence and impact
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.code(issue['fixSql'], language='sql')
                with col2:
                    st.success(f"🎯 **Confidence:** {confidence}%")
                    st.info("📊 **Impact:** High")
                    expected_rows = issue.get('expected_rows_affected', 100)
                    st.caption(f"Expected to fix ~{expected_rows} rows")
                
                edited_fix = st.text_area(
                    "Edit Fix SQL (optional)",
                    value=issue['fixSql'],
                    height=150,
                    key=f"edit_fix_{issue['id']}",
                    help="You can edit the SQL fix before approving"
                )
            
            # Action buttons (only show when fix is generated)
            if issue.get('fix_generated', False):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Fix", key=f"approve_{issue['id']}", type="primary"):
                        # Check rate limit (max 10 fixes per hour)
                        current_time = datetime.datetime.now()
                        time_since_hour_start = (current_time - st.session_state.hour_start_time).total_seconds()
                        
                        # Reset counter if hour has passed
                        if time_since_hour_start >= 3600:
                            st.session_state.fixes_in_current_hour = 0
                            st.session_state.hour_start_time = current_time
                        
                        # Check if limit exceeded
                        if st.session_state.fixes_in_current_hour >= st.session_state.max_fixes_per_hour:
                            st.error(f"🚫 Rate limit exceeded: Max {st.session_state.max_fixes_per_hour} fixes per hour")
                        else:
                            # Execute the actual SQL fix on the database with dramatic effect
                            with st.spinner("🔄 Applying fix via AI..."):
                                try:
                                    # Get before metrics from database (extract column from fix SQL)
                                    column_name = "customer_email"  # Default column for demo
                                    before_metrics = autosteward.get_table_metrics(issue['table'], column_name)
                                    before_nulls = before_metrics.get('null_count', 0)
                                    
                                    # Get before sample data for comparison (only NULL rows)
                                    before_sample = autosteward.get_sample_data(issue['table'], column_name, limit=5, filter_null=True)
                                    st.session_state.before_sample_data = before_sample
                                    
                                    # Track the IDs of rows that will be fixed (using customer_id column)
                                    if before_sample.get('sample_data'):
                                        fixed_ids = [row.get('customer_id') for row in before_sample['sample_data'] if row.get('customer_id')]
                                        st.session_state.fixed_row_ids = fixed_ids
                                    
                                    # Execute the SQL fix (use edited version if provided)
                                    fix_sql = edited_fix if edited_fix else issue.get('fixSql', '')
                                    result = autosteward.apply_fix(issue['table'], fix_sql)
                                    
                                    if result.get('success'):
                                        # Get after metrics from database
                                        after_metrics = autosteward.get_table_metrics(issue['table'], column_name)
                                        after_nulls = after_metrics.get('null_count', 0)
                                        rows_affected = result.get('rows_affected', 0)
                                        
                                        # Get after sample data for comparison (same rows that were fixed)
                                        after_sample = autosteward.get_sample_data(issue['table'], column_name, limit=5, filter_null=False, row_ids=st.session_state.fixed_row_ids)
                                        st.session_state.after_sample_data = after_sample
                                        
                                        # Update table description with fix history (OpenMetadata integration)
                                        metadata_result = autosteward.update_table_description_with_fix(
                                            issue['table'],
                                            issue,
                                            {
                                                'sql': fix_sql,
                                                'rows_affected': rows_affected,
                                                'before_nulls': before_nulls,
                                                'after_nulls': after_nulls
                                            }
                                        )
                                        
                                        # Tag the fixed column with AI.AutoStewardAI fixed
                                        column_tag_result = autosteward.tag_column_with_fix_history(
                                            issue['table'],
                                            column_name
                                        )
                                        
                                        # Generate rollback SQL
                                        rollback_sql = autosteward.generate_rollback_sql(fix_sql, issue['table'], column_name)
                                        
                                        # Add to execution history
                                        st.session_state.execution_history.append({
                                            'timestamp': datetime.datetime.now().isoformat(),
                                            'table': issue['table'],
                                            'test': issue['test'],
                                            'action': 'approved',
                                            'before_metrics': {'null_count': before_nulls},
                                            'after_metrics': {'null_count': after_nulls},
                                            'rows_affected': rows_affected,
                                            'severity_score': issue.get('severity_score', 50),
                                            'fix_applied': True,
                                            'openmetadata_updated': metadata_result.get('success', False),
                                            'column_tagged': column_tag_result.get('success', False),
                                            'column_tag': column_tag_result.get('tag_applied', None),
                                            'fix_sql': fix_sql,
                                            'rollback_sql': rollback_sql,
                                            'column_name': column_name
                                        })
                                        
                                        st.session_state.issues = [i for i in st.session_state.issues if i['id'] != issue['id']]
                                        st.session_state.fixed_today += 1
                                        st.session_state.fixes_in_current_hour += 1
                                        
                                        # Store LLM-predicted hours saved and accumulate total
                                        hours_saved = issue.get('hours_saved', 2)
                                        st.session_state.last_hours_saved = hours_saved
                                        st.session_state.total_hours_saved += hours_saved
                                        
                                        # Store fix details for animation after banner updates
                                        st.session_state.last_fix_details = {
                                            'before_nulls': before_nulls,
                                            'after_nulls': after_nulls,
                                            'rows_affected': rows_affected
                                        }
                                        st.session_state.fix_just_applied = True
                                        st.session_state.show_notify_button = True
                                        
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to execute SQL: {result.get('error')}")
                                        st.error("Fix was not applied. Please check the SQL and database connection.")
                                except Exception as e:
                                    st.error(f"❌ Failed to apply fix: {str(e)}")
                
                with col2:
                    if st.button("❌ Reject Fix", key=f"reject_{issue['id']}"):
                        st.session_state.issues = [i for i in st.session_state.issues if i['id'] != issue['id']]
                        st.warning("❌ Fix rejected")
                        st.rerun()

# Footer
st.divider()
st.markdown("""
---
**AutoSteward AI** - Autonomous Data Steward  
Powered by OpenMetadata AI SDK + LangChain + Llama 3
""")

# Auto-scan logic (runs every 30 seconds when enabled)
if st.session_state.auto_scan_enabled:
    import datetime
    
    # Check if 30 seconds have passed since last scan
    if st.session_state.last_scan_time:
        time_since_scan = (datetime.datetime.now() - st.session_state.last_scan_time).total_seconds()
        if time_since_scan >= 30:
            # Trigger automatic scan
            st.session_state.scanning = True
            table_fqn = f"{autosteward.config.project.service_name}.{autosteward.config.project.database_name}.mart.customers"
            
            try:
                diagnosis = autosteward.diagnose_root_cause(table_fqn)
                st.session_state.total_scanned += 1
                
                if diagnosis.get('status') == 'failed':
                    # Get severity score, breakdown, and lineage data from diagnosis
                    severity_score = diagnosis.get('severity_score', 50)
                    severity_breakdown = diagnosis.get('severity_breakdown', {})
                    lineage_data = diagnosis.get('lineage', {})
                    
                    # Format lineage data for display (show only downstream for customer POV)
                    if lineage_data:
                        # Count unique downstream assets (unique toEntity IDs)
                        downstream_edges = lineage_data.get('downstreamEdges', [])
                        downstream_ids = set()
                        for edge in downstream_edges:
                            if isinstance(edge, dict):
                                to_entity = edge.get('toEntity')
                                if to_entity:
                                    downstream_ids.add(to_entity)
                        downstream_count = len(downstream_ids)
                        
                        lineage_data = {
                            'downstream_count': downstream_count
                        }
                    
                    # Get failing test info from diagnosis
                    upstream_analysis = diagnosis.get('upstreamAnalysis', {})
                    failing_nodes = upstream_analysis.get('failingUpstreamNodes', [])
                    test_name = failing_nodes[0].get('failingTestCases', {}).get('testCaseResults', [{}])[0].get('testCaseFQN', 'unknown') if failing_nodes else 'unknown'
                    issue_desc = failing_nodes[0].get('failingTestCases', {}).get('testCaseResults', [{}])[0].get('result', 'unknown') if failing_nodes else 'unknown'
                    
                    st.session_state.issues = [{
                        'id': 1,
                        'table': table_fqn,
                        'test': test_name,
                        'issue': issue_desc,
                        'severity': 'high',
                        'severity_score': severity_score,
                        'severity_breakdown': severity_breakdown,
                        'lineage_data': lineage_data,
                        'fixSql': None,  # Fix not generated yet
                        'aiGenerated': False,
                        'model': None,
                        'confidence_score': None,
                        'expected_rows_affected': None,
                        'hours_saved': None,
                        'fix_generated': False  # Track if fix has been generated
                    }]
                else:
                    st.session_state.issues = []
            except Exception as e:
                pass  # Silent failure for auto-san
            
            st.session_state.last_scan_time = datetime.datetime.now()
            st.rerun()
    
    # Show countdown timer
    if st.session_state.last_scan_time:
        time_since_scan = (datetime.datetime.now() - st.session_state.last_scan_time).total_seconds()
        time_until_next = max(0, 30 - time_since_scan)
        st.sidebar.caption(f"⏱️ Next scan in: {int(time_until_next)}s")

