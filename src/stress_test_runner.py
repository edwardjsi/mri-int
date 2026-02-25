import os
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the scenarios
SCENARIOS = [
    {
        "name": "Baseline Engine",
        "prefix": "baseline_",
        "start": None,
        "end": None,
        "tx_cost": 0.004
    },
    {
        "name": "High Transaction Friction (0.8%)",
        "prefix": "high_friction_",
        "start": None,
        "end": None,
        "tx_cost": 0.008
    },
    {
        "name": "2008 Financial Crisis",
        "prefix": "crash_2008_",
        "start": "2007-10-01",
        "end": "2009-03-31",
        "tx_cost": 0.004
    },
    {
        "name": "2020 COVID Crash",
        "prefix": "crash_2020_",
        "start": "2020-01-01",
        "end": "2020-06-30",
        "tx_cost": 0.004
    },
    {
        "name": "Sideways Market",
        "prefix": "sideways_2010_",
        "start": "2010-01-01",
        "end": "2013-12-31",
        "tx_cost": 0.004
    },
    {
        "name": "Walk-Forward (In-Sample Training)",
        "prefix": "wf_train_",
        "start": "2005-01-01",
        "end": "2015-12-31",
        "tx_cost": 0.004
    },
    {
        "name": "Walk-Forward (Out-of-Sample Test)",
        "prefix": "wf_test_",
        "start": "2016-01-01",
        "end": "2024-12-31",
        "tx_cost": 0.004
    }
]

def run_scenario(scenario):
    logger.info(f"\n{'='*60}\nRUNNING SCENARIO: {scenario['name']}\n{'='*60}")
    
    # Build Portfolio Command
    port_cmd = ["python", "-m", "src.portfolio_engine"]
    if scenario['start']:
        port_cmd.extend(["--start-date", scenario['start']])
    if scenario['end']:
        port_cmd.extend(["--end-date", scenario['end']])
        
    port_cmd.extend(["--tx-cost", str(scenario['tx_cost'])])
    port_cmd.extend(["--output-prefix", scenario['prefix']])
    
    logger.info(f"Executing: {' '.join(port_cmd)}")
    subprocess.run(port_cmd, check=True)
    
    # Build Metrics Command
    metrics_cmd = ["python", "-m", "src.metrics_engine", "--input-prefix", scenario['prefix']]
    logger.info(f"Executing: {' '.join(metrics_cmd)}")
    subprocess.run(metrics_cmd, check=True)

def main():
    logger.info("Initializing Final Phase 10 Stress Tests...")
    
    # Ensure outputs directory is clean/ready
    os.makedirs('outputs', exist_ok=True)
    
    for scenario in SCENARIOS:
        try:
            run_scenario(scenario)
        except subprocess.CalledProcessError as e:
            logger.error(f"Scenario '{scenario['name']}' failed: {e}")
            break
            
    logger.info("\nAll scenarios complete! Check the outputs directory for individual test prefix CSVs/MDs.")

if __name__ == "__main__":
    main()
