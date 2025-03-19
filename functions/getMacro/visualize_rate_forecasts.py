#!/usr/bin/env python3
"""
[FILENAME] visualize_rate_forecasts.py
[DESCRIPTION] Visualizes rate forecasts from different sources
Author: JP + [2024-07-19]
"""

import json
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

def load_results(file_path):
    """Load results from a JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def convert_date(date_str):
    """Convert date string to datetime object"""
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except:
        # If date can't be parsed, return None
        return None

def visualize_rate_forecasts(results_file):
    """Visualize rate forecasts from different sources"""
    # Load results
    results = load_results(results_file)
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 1, figsize=(12, 14), gridspec_kw={'height_ratios': [2, 1]})
    
    # --- First plot: Meeting expectations by date ---
    ax1 = axes[0]
    ax1.set_title("Fed Rate Expectations by Meeting Date", fontsize=16)
    
    # Prepare data for first plot
    meeting_data = []
    
    # Process each source
    for source_name, data in results.items():
        if 'result' in data:
            data = data['result']
            
        for meeting in data.get('meetings', []):
            meeting_date = convert_date(meeting.get('date'))
            if meeting_date:
                meeting_data.append({
                    'date': meeting_date,
                    'rate': meeting.get('expected_rate', 0) * 100,  # Convert to basis points
                    'probability': meeting.get('probability', 0) * 100,  # Convert to percentage
                    'source': source_name
                })
    
    # Convert to DataFrame
    if meeting_data:
        df_meetings = pd.DataFrame(meeting_data)
        
        # Group by source
        for source, group in df_meetings.groupby('source'):
            ax1.plot(group['date'], group['rate'], 'o-', label=source, markersize=8)
            
        # Format x-axis to show dates nicely
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d, %Y'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        ax1.set_ylabel('Expected Rate (basis points)', fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend(fontsize=10)
    else:
        ax1.text(0.5, 0.5, 'No meeting data available', 
                 horizontalalignment='center', verticalalignment='center', 
                 transform=ax1.transAxes, fontsize=14)
    
    # --- Second plot: Current rates by different sources ---
    ax2 = axes[1]
    ax2.set_title("Current Fed Rate by Different Sources", fontsize=16)
    
    # Prepare data for second plot
    current_rates = []
    
    # Process each source
    for source_name, data in results.items():
        if 'result' in data:
            data = data['result']
            
        # Extract current rate from bank_forecasts
        for forecast in data.get('bank_forecasts', []):
            if 'rate_current' in forecast:
                current_rates.append({
                    'source': forecast.get('bank', source_name),
                    'rate': forecast.get('rate_current', 0) * 100  # Convert to basis points
                })
        
        # Also look for current rate in the raw response
        if 'raw_response' in data:
            import re
            current_rate_match = re.search(r"[Cc]urrent (?:[Tt]arget|[Ff]ederal [Ff]unds) [Rr]ate:?\s*(\d+\.?\d*)", 
                                          data['raw_response'])
            if current_rate_match:
                rate = float(current_rate_match.group(1))
                # Only add if we don't already have this source
                if not any(item['source'] == source_name for item in current_rates):
                    current_rates.append({
                        'source': source_name,
                        'rate': rate
                    })
    
    # Convert to DataFrame and plot
    if current_rates:
        df_current = pd.DataFrame(current_rates)
        
        # Sort by rate value
        df_current = df_current.sort_values('rate')
        
        # Plot horizontal bar chart
        bars = ax2.barh(df_current['source'], df_current['rate'], height=0.6)
        
        # Add rate values at the end of each bar
        for i, bar in enumerate(bars):
            ax2.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                    f"{df_current['rate'].iloc[i]:.2f} bps", 
                    va='center', fontsize=10)
        
        ax2.set_xlabel('Rate (basis points)', fontsize=12)
        ax2.grid(True, linestyle='--', alpha=0.7, axis='x')
    else:
        ax2.text(0.5, 0.5, 'No current rate data available', 
                horizontalalignment='center', verticalalignment='center', 
                transform=ax2.transAxes, fontsize=14)
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = Path('image_snaps/rate_forecast_visualization.png')
    plt.savefig(output_file)
    print(f"Visualization saved to: {output_file.absolute()}")
    
    # Show plot
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize rate forecasts from different sources')
    parser.add_argument('--file', default='image_snaps/debug_extraction_results.json',
                       help='JSON file with extraction results')
    
    args = parser.parse_args()
    visualize_rate_forecasts(args.file) 