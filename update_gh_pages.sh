#!/bin/bash
# Script to update the GitHub Pages site with fresh portfolio data

# Activate virtual environment
source venv/bin/activate

# Create required directories
mkdir -p docs/data
mkdir -p docs/js
mkdir -p docs/css

# Create CSS file if it doesn't exist
if [ ! -f docs/styles.css ]; then
  cat > docs/styles.css << EOF
/* Portfolio Dashboard Styles */
.card {
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card-header {
  background-color: #f8f9fa;
  font-weight: bold;
}

.text-success {
  font-weight: 500;
}

.text-danger {
  font-weight: 500;
}
EOF
fi

# Create the streamlit.html file for embedding the Streamlit app
cat > docs/streamlit.html << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Portfolio Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            overflow: hidden;
        }
        .streamlit-embed {
            width: 100%;
            height: 100vh;
            border: none;
        }
        .back-button {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
            opacity: 0.8;
        }
        .back-button:hover {
            opacity: 1;
        }
    </style>
</head>
<body>
    <!-- Replace this URL with your actual Streamlit Cloud URL -->
    <iframe 
        src="STREAMLIT_URL_HERE/?embedded=true" 
        class="streamlit-embed"
        allowfullscreen
    ></iframe>
    
    <a href="index.html" class="btn btn-primary back-button">
        &larr; Back to Static Dashboard
    </a>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

echo "Generating fresh portfolio data..."
# Generate portfolio data with default 60/40 portfolio
python scripts/generate_static_data.py

echo "Updating GitHub repository..."
# Commit and push changes
git add docs
git commit -m "Update portfolio data for GitHub Pages"
git push origin main

echo "Portfolio dashboard updated successfully!"
echo "View your dashboard at: https://yourusername.github.io/your-repo-name/" 