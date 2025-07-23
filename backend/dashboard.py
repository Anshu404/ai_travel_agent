from flask import Flask, render_template
import sqlite3
import json

app = Flask(__name__)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # The check_same_thread=False is important for Flask's multi-threaded environment
    conn = sqlite3.connect('agent_logs.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Renders the main dashboard with all analytical data."""
    conn = get_db_connection()
    
    # === 1. Key Performance Indicators (KPIs) ===
    total_messages = conn.execute('SELECT COUNT(*) FROM interactions').fetchone()[0]
    total_conversations = conn.execute('SELECT COUNT(DISTINCT session_id) FROM interactions').fetchone()[0]
    
    # A simple way to estimate errors by looking for keywords in the agent's response
    total_errors = conn.execute("SELECT COUNT(*) FROM interactions WHERE agent_response LIKE '%error%' OR agent_response LIKE '%sorry%' OR agent_response LIKE '%apologize%'").fetchone()[0]
    
    # Calculate average messages per session, handling division by zero
    avg_messages = (total_messages / total_conversations) if total_conversations > 0 else 0

    # === 2. Data for Charts ===
    
    # Chart 1: Tool Usage (Bar Chart)
    tool_usage = conn.execute("SELECT tool_used, COUNT(*) as count FROM interactions WHERE tool_used != 'None' AND tool_used IS NOT NULL GROUP BY tool_used ORDER BY count DESC").fetchall()
    tool_labels = json.dumps([row['tool_used'] for row in tool_usage])
    tool_counts = json.dumps([row['count'] for row in tool_usage])

    # Chart 2: Interactions Over Time (Line Chart)
    # Fetches the last 15 days of activity
    interactions_over_time = conn.execute("SELECT STRFTIME('%Y-%m-%d', timestamp) as day, COUNT(*) as count FROM interactions GROUP BY day ORDER BY day DESC LIMIT 15").fetchall()
    # Reverse the lists so the chart shows time progressing from left to right
    time_labels = json.dumps([row['day'] for row in reversed(interactions_over_time)])
    time_counts = json.dumps([row['count'] for row in reversed(interactions_over_time)])

    # Chart 3: Channel Usage (Pie Chart)
    channel_distribution = conn.execute("SELECT channel, COUNT(*) as count FROM interactions GROUP BY channel").fetchall()
    channel_labels = json.dumps([row['channel'] for row in channel_distribution])
    channel_counts = json.dumps([row['count'] for row in channel_distribution])

    # === 3. Data for Recent Interactions Table ===
    recent_interactions = conn.execute('SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 50').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                           # KPIs
                           total_messages=total_messages,
                           total_conversations=total_conversations,
                           total_errors=total_errors,
                           avg_messages=f"{avg_messages:.1f}",
                           # Chart Data
                           tool_labels=tool_labels,
                           tool_counts=tool_counts,
                           time_labels=time_labels,
                           time_counts=time_counts,
                           channel_labels=channel_labels,
                           channel_counts=channel_counts,
                           # Table Data
                           recent_interactions=recent_interactions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)