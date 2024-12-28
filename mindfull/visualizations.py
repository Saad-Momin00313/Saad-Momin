import plotly.graph_objects as go

def create_mood_chart(mood_data):
    """Create a line chart showing mood and energy levels over time."""
    fig = go.Figure()
    
    # Add mood line
    fig.add_trace(go.Scatter(
        x=mood_data['dates'],
        y=mood_data['mood_values'],
        name='Mood',
        line=dict(color='#FF9999', width=2),
        mode='lines+markers'
    ))
    
    # Add energy line
    fig.add_trace(go.Scatter(
        x=mood_data['dates'],
        y=mood_data['energy_values'],
        name='Energy',
        line=dict(color='#66B2FF', width=2),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        title='Mood & Energy Trends',
        xaxis_title='Date',
        yaxis_title='Level',
        template='plotly_dark',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_practice_heatmap(data):
    """Create a heatmap showing practice intensity across days."""
    fig = go.Figure(data=go.Heatmap(
        z=data['values'],
        x=data['dates'],
        colorscale='Viridis',
        showscale=True
    ))
    
    fig.update_layout(
        title='Practice Intensity',
        xaxis_title='Day of Week',
        yaxis_title='Week',
        template='plotly_dark'
    )
    
    return fig