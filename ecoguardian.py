import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # 🌲 EcoGuardian: San Diego Wildlife Guardian
    ### *AI-Powered Hotspot Detection & Ranger Safety Broadcast*

    ---
    **Instructions:** Select a species and adjust the detection parameters to identify clusters.
    Click **Generate Ranger Alert** to create an AI voice advisory for the primary hotspot.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    from sklearn.cluster import DBSCAN
    import plotly.express as px
    import plotly.graph_objects as go
    from google import genai
    import requests
    from scipy.spatial import ConvexHull
    import base64

    return ConvexHull, DBSCAN, genai, go, mo, np, pd, px, requests


@app.cell
def _():
    # API Keys and ID
    GEMINI_KEY = ...
    ELEVEN_KEY = ...
    VOICE_ID = ...
    return ELEVEN_KEY, GEMINI_KEY, VOICE_ID


@app.cell
def _(mo):
    base_path = r"C:\Users\crist\Downloads\EcoGuardian\Dropdown Observations\\"

    # UI Elements
    species_dropdown = mo.ui.dropdown(
        options={
            "Coyote": base_path + "Coyote.csv", 
            "Leopard Shark": base_path + "Leopard Shark.csv",
            "Torrey Pine": base_path + "Torrey Pine.csv",
            "Garibaldi": base_path + "Garibaldi.csv"
        },
        value="Coyote", 
        label="Select Target Species:"
    )
    return (species_dropdown,)


@app.cell
def _(mo):
    radius_slider = mo.ui.slider(start=0.05, stop=2.0, step=0.05, value=0.25, label="Search Radius (Miles)")
    min_pack_slider = mo.ui.slider(start=2, stop=20, step=1, value=5, label="Min. Sightings")
    ranger_button = mo.ui.run_button(label="Generate Ranger Alert", kind="success")
    return min_pack_slider, radius_slider, ranger_button


@app.cell
def _(pd, species_dropdown):
    # Load and Clean Data
    raw_data = pd.read_csv(species_dropdown.value)
    clean_species_df = raw_data[['latitude', 'longitude', 'observed_on', 'common_name']].dropna()
    current_name = clean_species_df['common_name'].iloc[0]
    return clean_species_df, current_name


@app.cell
def _(DBSCAN, clean_species_df, min_pack_slider, np, radius_slider):
    # Machine Learning
    coords_rad = np.radians(clean_species_df[['latitude', 'longitude']].values)
    eps_rad = radius_slider.value / 3958.8 
    db = DBSCAN(eps=eps_rad, min_samples=min_pack_slider.value, metric='haversine', algorithm='ball_tree').fit(coords_rad)
    clean_species_df['cluster'] = db.labels_

    # Separate Clusters
    hotspots = clean_species_df[clean_species_df['cluster'] != -1]
    noise = clean_species_df[clean_species_df['cluster'] == -1]
    return hotspots, noise


@app.cell
def _(
    ConvexHull,
    go,
    hotspots,
    min_pack_slider,
    mo,
    noise,
    np,
    px,
    radius_slider,
    ranger_button,
    species_dropdown,
):
    # Map Setup
    fig = px.scatter_map(noise, lat="latitude", lon="longitude", color_discrete_sequence=["#cccccc"], zoom=10, height=500)

    best_cluster = None
    if not hotspots.empty:
        # Add colored dots for all packs
        cluster_fig = px.scatter_map(hotspots, lat="latitude", lon="longitude", color=hotspots['cluster'].astype(str))
        for trace in cluster_fig.data: fig.add_trace(trace)

        # Find the largest pack ID
        best_id = hotspots['cluster'].value_counts().idxmax()
        best_cluster = hotspots[hotspots['cluster'] == best_id]

        # Loop through all clusters to draw boundaries
        for cluster_id in hotspots['cluster'].unique():
            cluster_data = hotspots[hotspots['cluster'] == cluster_id]

            # Convex Hull needs at least 3 points
            if len(cluster_data) >= 3:
                points = cluster_data[['latitude', 'longitude']].values

                try:
                    hull = ConvexHull(points)

                    hull_lat = points[hull.vertices, 0]
                    hull_lon = points[hull.vertices, 1]
                    hull_lat = np.append(hull_lat, hull_lat[0])
                    hull_lon = np.append(hull_lon, hull_lon[0])

                    is_largest = (cluster_id == best_id)
                    fill_color = 'rgba(255, 0, 0, 0.25)' if is_largest else 'rgba(255, 165, 0, 0.1)'
                    line_color = 'red' if is_largest else 'black'
                    line_width = 3 if is_largest else 1

                    fig.add_trace(go.Scattermap(
                        lat=hull_lat, 
                        lon=hull_lon, 
                        mode='lines', 
                        fill='toself',
                        fillcolor=fill_color,
                        line=dict(color=line_color, width=line_width),
                        name=f"Cluster {cluster_id}"
                    ))
                except Exception:
                    pass


        # Highlight centroids
        centroids = hotspots.groupby('cluster')[['latitude', 'longitude']].mean().reset_index()

        largest_centroid = centroids[centroids['cluster'] == best_id]
        other_centroids = centroids[centroids['cluster'] != best_id]

        # Label the Primary Hotspot
        fig.add_trace(go.Scattermap(
            lat=largest_centroid['latitude'], 
            lon=largest_centroid['longitude'], 
            mode='markers+text', 
            marker=go.scattermap.Marker(size=16, color='darkred', opacity=0.9),
            text=["🚨 PRIMARY HOTSPOT"],
            textposition="top center",
            textfont=dict(color='red', size=16)
        ))

        # Dot the smaller hotspots
        if not other_centroids.empty:
            fig.add_trace(go.Scattermap(
                lat=other_centroids['latitude'], 
                lon=other_centroids['longitude'], 
                mode='markers', 
                marker=go.scattermap.Marker(size=12, color='blue', opacity=0.7)
            ))

    fig.update_layout(map_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":40}, showlegend=False)

    mo.vstack([
        fig,
        mo.hstack([species_dropdown, radius_slider, min_pack_slider, ranger_button], justify="center")
    ], gap=1)
    return (best_cluster,)


@app.cell
def _(
    ELEVEN_KEY,
    GEMINI_KEY,
    VOICE_ID,
    best_cluster,
    current_name,
    genai,
    mo,
    ranger_button,
    requests,
):
    mo.stop(not ranger_button.value, mo.md("*(Click the button above to generate a voice alert)*"))

    # 1. Create a variable to hold our final screen
    final_output = mo.md("Processing...") 

    if best_cluster is not None:
        client = genai.Client(api_key=GEMINI_KEY)

        try:
            # --- PHASE 1: Draft the Script ---
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=f"""
                Context: You are a Digital Park Ranger for San Diego.
                Data: We detected {len(best_cluster)} {current_name} sightings at GPS coordinates {best_cluster['latitude'].mean():.4f}, {best_cluster['longitude'].mean():.4f}.
                Task: 
                1. Identify the nearest local beach, park, or neighborhood.
                2. Tell the user the best specific spot to see {current_name} in that area.
                3. Mention the best time of day for sightings (e.g. dawn/dusk).
                4. Provide a safety warning: "Proceed with caution; if threatened, do not approach."
                5. CRITICAL: DO NOT read the raw GPS numbers.
                Format: Plain text only, no markdown.
                """
            )
            ranger_script = response.text

            # --- PHASE 2: Generate the Audio ---
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
            payload = {
                "text": ranger_script, 
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
            }

            audio_res = requests.post(url, json=payload, headers=headers)

            if audio_res.status_code == 200:
                # Save the raw audio locally
                with open("ranger_alert.mp3", "wb") as f:
                    f.write(audio_res.content)

                # Read it back as raw bytes to bypass any browser pathing errors
                with open("ranger_alert.mp3", "rb") as f:
                    audio_bytes = f.read()

                # --- PHASE 3: Assign the UI to our variable ---
                final_output = mo.vstack([
                    mo.md(f"### 🌲 Ranger Advisory\n**{ranger_script}**"),
                    mo.audio(src=audio_bytes) 
                ])
            else:
                final_output = mo.md(f"⚠️ **ElevenLabs Error {audio_res.status_code}:** {audio_res.text}")

        except Exception as e:
            final_output = mo.md(f"⚠️ **API Error:** {str(e)}")
    else:
        final_output = mo.md("No hotspots found on the map.")

    # THE MAGIC LINE: This must be the absolute last line in the cell!
    final_output
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
