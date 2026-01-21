# Baijerilainen 🏎️

**Bayesian Optimization for ECU Fuel Mapping**

A modern web application for optimizing Brake Specific Fuel Consumption (BSFC) using Bayesian optimization on MoTeC M1 dyno log data. Upload your tune logs, let the algorithm find optimal Lambda and Ignition Timing values, and get actionable suggestions for your next dyno runs.

## 🛠️ Modern Tech Stack

This project embraces cutting-edge tooling for a fast, efficient development experience:

- **[Bun](https://bun.sh/)** - Ultra-fast JavaScript runtime and package manager (replacing Node.js + npm)
- **[uv](https://github.com/astral-sh/uv)** - Blazingly fast Python package manager (replacing pip/poetry)
- **[SvelteKit](https://kit.svelte.dev/)** - Full-stack web framework with Svelte 5 and runes
- **[TailwindCSS v4](https://tailwindcss.com/)** - Utility-first CSS framework
- **[scikit-optimize](https://scikit-optimize.github.io/)** - Bayesian optimization library

The frontend handles data upload, visualization, and results display, while the Python backend performs the heavy lifting of Gaussian Process fitting and optimization.

## 📋 Prerequisites

### For Local Development
- [Bun](https://bun.sh/) (v1.0+)
- [uv](https://github.com/astral-sh/uv) (for Python package management)
- Python 3.9+

### For Docker Development
- Docker & Docker Compose

## 🚀 Getting Started

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd baijerilainen

# Start the development server
docker-compose up --build
```

The app will be available at `http://localhost:5173`

### Option 2: Local Development

```bash
# Install JavaScript dependencies
bun install

# Install Python dependencies
uv sync

# Start the development server
bun run dev
```

## 📊 How It Works

### Data Preparation

1. **Record dyno runs** with your MoTeC M1 ECU, varying Lambda and Ignition Timing across different RPM ranges
2. **Export logs** using MoTeC i2 Pro: `File → Export → CSV Export...`
3. **Required channels:**
   - `Engine Speed` (RPM)
   - `Fuel Mixture Aim` (Lambda target)
   - `Ignition Timing Main` (degrees BTDC)
   - `Dyno Brake Specific Fuel Consumption` (g/kWh)

### Upload & Process

1. Open the web interface at `http://localhost:5173`
2. Drag and drop your exported CSV files
3. Click **Save & Continue** to start the optimization

### The Optimization Process

The optimization runs through a 5-step pipeline:

#### Step 1: Data Loading
All CSV files are parsed and validated. Invalid BSFC readings (zeros, indicating no load) are filtered out.

#### Step 2: RPM Binning
Data is grouped into RPM bins (default 50 RPM width). This reduces noise and ensures adequate coverage across the operating range. Bins with fewer than 3 samples are discarded.

#### Step 3: Gaussian Process Fitting
A **Gaussian Process (GP)** surrogate model is fitted to the data:
- **Input features:** Lambda, Ignition Timing, RPM
- **Output:** BSFC
- **Kernel:** Matérn 5/2 (well-suited for smooth physical processes)

The GP learns the response surface of how BSFC varies with tune parameters, including uncertainty estimates.

#### Step 4: Bayesian Optimization
For each RPM bin, the optimizer searches for the Lambda and Timing combination that minimizes BSFC:

1. **Expected Improvement (EI)** acquisition function balances exploitation (finding the minimum) with exploration (reducing uncertainty)
2. **Multi-start optimization** ensures global optima are found
3. **Next experiments** are suggested where the model is most uncertain or expects improvement

#### Step 5: Results Export
Results are saved as JSON with:
- **Optimal ECU map:** Best Lambda and Timing for each RPM bin
- **Suggested experiments:** Next dyno runs to refine the model
- **Visualization data:** For interactive charts

### Iterative Improvement

This is designed as an **iterative process**:

```
┌─────────────────┐
│  Upload Logs    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Run Optimizer  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  View Results   │
│  & Suggestions  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Run Dyno Tests │◄──┐
│  with Suggested │   │
│  Parameters     │   │
└────────┬────────┘   │
         ▼            │
┌─────────────────┐   │
│  Export New CSV │   │
│  from MoTeC     │───┘
└─────────────────┘
```

Each iteration adds more data points, improving the GP model's accuracy and converging on the true optimal tune.

## 📁 Project Structure

```
baijerilainen/
├── src/
│   ├── routes/              # SvelteKit pages
│   │   ├── +page.svelte     # File upload UI
│   │   ├── run/             # Optimization progress
│   │   └── results/         # Results viewer
│   ├── lib/                 # Shared utilities
│   └── components/          # Svelte components
├── bayesian_optimization/   # Python optimization engine
│   ├── data_loader.py       # CSV parsing
│   ├── rpm_binning.py       # Data preprocessing
│   ├── gp_model.py          # Gaussian Process model
│   ├── optimizer.py         # Bayesian optimizer
│   └── exporter.py          # Results export
├── data/                    # Input CSV files
├── results/                 # Optimization outputs
├── main.py                  # CLI entry point
├── Dockerfile
└── docker-compose.yml
```

## 🔧 Configuration

Default optimization parameters can be adjusted in `main.py`:

```python
RPM_BIN_WIDTH = 50        # RPM resolution (smaller = more bins)
MIN_SAMPLES_PER_BIN = 3   # Minimum data points per bin
N_SUGGESTIONS = 5         # Number of experiments to suggest
LAMBDA_BOUNDS = None      # Auto-detect from data
TIMING_BOUNDS = None      # Auto-detect from data
```

## 📈 Understanding Results

### Optimal ECU Map
A table showing the recommended Lambda and Timing for each RPM bin, along with:
- **Predicted BSFC:** Model's estimate of fuel consumption
- **Uncertainty:** How confident the model is (lower = more certain)

### Suggested Experiments
The most valuable dyno runs to perform next:
- High uncertainty regions (model needs more data)
- Promising regions (potential for improvement)

### Visualization
Interactive charts showing:
- Lambda and Timing distributions across RPM
- BSFC response surface
- Model uncertainty

## ⚠️ Important Notes

- **Data quality matters:** Ensure steady-state measurements with accurate dyno load
- **Safety first:** Always verify suggested timing values are safe for your engine
- **Iterative process:** 3-5 optimization rounds typically yield good results
- **Physical constraints:** The optimizer doesn't know your engine's limits—apply engineering judgment

## 📄 License

MIT

## 🙏 Acknowledgments

- MoTeC for excellent ECU and logging systems
- scikit-optimize team for the Bayesian optimization library
- Svelte team for the delightful framework
