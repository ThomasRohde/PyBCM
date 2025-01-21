# Business Capability Model (BCM)

A FastAPI and React application for managing business capability models.

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- npm 9 or higher

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PyBCM.git
cd PyBCM
```

2. Set up the Python backend:
```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. Set up the React client:
```bash
cd bcm-client
npm install
npm run build
```

## Running the Application

1. Start the FastAPI server:
```bash
# From the root directory
uvicorn bcm.api.server:app --reload
```
The API will be available at http://localhost:8000

2. Start the React development server (optional, for development only):
```bash
cd bcm-client
npm run dev
```
The development server will be available at http://localhost:5173

## Production Use

For production use, the FastAPI server will serve the built React client automatically. Simply:

1. Build the client (if you haven't already):
```bash
cd bcm-client
npm run build
```

2. Start the FastAPI server:
```bash
uvicorn bcm.api.server:app
```

The complete application will be available at http://localhost:8000
