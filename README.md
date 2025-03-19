# macOS WiFi Network Monitor

A Python utility to monitor WiFi network quality over time and detect connection glitches on macOS systems.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.6%2B-brightgreen)

## Overview

This tool helps diagnose intermittent WiFi issues by collecting and analyzing network metrics over time. It runs in the background, periodically sampling your WiFi connection's health and recording metrics such as signal strength, latency, packet loss, and connection status.

The tool can identify network "glitches" based on configurable thresholds and generates both real-time output and a detailed CSV report for further analysis.

![Sample Screenshot](https://via.placeholder.com/800x400?text=WiFi+Monitor+Screenshot)

## Features

- 📊 **Comprehensive Metrics**: Tracks RSSI (signal strength), latency, packet loss, noise levels, and transmission rates
- ⚠️ **Glitch Detection**: Automatically flags problematic network conditions based on configurable thresholds
- 📈 **Data Export**: Saves all metrics to CSV for detailed analysis and visualization
- 📱 **Live Monitoring**: Real-time terminal output showing current network status
- 📑 **Summary Reports**: Generates statistical overview when monitoring completes
- ⚙️ **Configurable**: Adjust monitoring duration, sampling interval, and thresholds via command-line options

## Requirements

- macOS (tested on macOS Monterey, Big Sur, and Catalina)
- Python 3.6 or higher

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/macos-wifi-monitor.git
   cd macos-wifi-monitor
   ```

2. No external dependencies are required beyond Python's standard library.

## Usage

Basic usage:

```bash
python3 wifi_monitor.py
```

This will monitor your WiFi for 60 minutes with measurements every 5 seconds.

For best results (to access all WiFi metrics), run with administrative privileges:

```bash
sudo python3 wifi_monitor.py
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `-d, --duration MINUTES` | Monitoring duration in minutes (default: 60) |
| `-i, --interval SECONDS` | Ping interval in seconds (default: 5) |
| `-t, --target HOST` | Ping target (default: 8.8.8.8) |
| `-o, --output FILE` | Output CSV file (default: wifi_monitor_results.csv) |
| `-l, --latency-threshold MS` | Latency glitch threshold in ms (default: 100) |
| `-p, --packet-loss-threshold PERCENT` | Packet loss glitch threshold in percent (default: 10.0) |
| `-r, --rssi-threshold DBM` | RSSI glitch threshold in dBm (default: -70) |

### Examples

Monitor for 2 hours, taking measurements every 10 seconds:
```bash
python3 wifi_monitor.py --duration 120 --interval 10
```

Use a custom ping target and output file:
```bash
python3 wifi_monitor.py --target 1.1.1.1 --output my_wifi_analysis.csv
```

Set custom thresholds for glitch detection:
```bash
python3 wifi_monitor.py --latency-threshold 150 --rssi-threshold -65
```

## Understanding the Results

### Real-time Output

While running, the tool displays:
- Timestamp of each measurement
- Current SSID (network name)
- RSSI in dBm (signal strength, higher is better)
- Average latency in milliseconds (lower is better)
- Packet loss percentage (lower is better)
- Glitch indicator (⚠️ when a glitch is detected)

### CSV Output

The CSV file contains detailed metrics for each measurement, including:
- Timestamp
- SSID
- Connection status
- Signal strength (RSSI)
- Noise level
- Transmission rate
- Latency statistics (min, avg, max, standard deviation)
- Packet loss percentage
- Glitch indicators by type (latency, packet loss, signal strength, connection)

### Interpreting Results

- **RSSI (Signal Strength)**: 
  - Excellent: -30 to -50 dBm
  - Good: -50 to -60 dBm
  - Fair: -60 to -70 dBm
  - Poor: Below -70 dBm

- **Latency**:
  - Excellent: < 20 ms
  - Good: 20-50 ms
  - Fair: 50-100 ms
  - Poor: > 100 ms

- **Packet Loss**:
  - Excellent: 0%
  - Good: < 1%
  - Fair: 1-2.5%
  - Poor: > 2.5%

## Visualizing Results

The CSV output can be easily imported into tools like Excel, Numbers, or Python data analysis libraries (pandas, matplotlib) for visualization.

Example visualization script (requires matplotlib and pandas):

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('wifi_monitor_results.csv')

# Convert timestamp to datetime
data['timestamp'] = pd.to_datetime(data['timestamp'])

# Create a figure with multiple subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

# Plot RSSI
ax1.plot(data['timestamp'], data['rssi_dbm'], 'b-')
ax1.set_ylabel('RSSI (dBm)')
ax1.set_title('WiFi Signal Strength Over Time')
ax1.grid(True)

# Plot latency
ax2.plot(data['timestamp'], data['avg_latency_ms'], 'g-')
ax2.set_ylabel('Latency (ms)')
ax2.set_title('Network Latency Over Time')
ax2.grid(True)

# Plot packet loss
ax3.plot(data['timestamp'], data['packet_loss_percent'], 'r-')
ax3.set_ylabel('Packet Loss (%)')
ax3.set_xlabel('Time')
ax3.set_title('Packet Loss Over Time')
ax3.grid(True)

plt.tight_layout()
plt.savefig('wifi_performance.png')
plt.show()
```

## Troubleshooting

### Permission Issues

If you encounter permission errors when running without sudo, try running with sudo to access all WiFi metrics:

```bash
sudo python3 wifi_monitor.py
```

### Airport Utility Not Found

If the script can't find the airport utility, you might need to locate it on your system:

```bash
find /System -name "airport"
```

Then update the `airport_path` variable in the script with the correct path.

### No Connection Information

If you're not seeing connection information, make sure your WiFi interface is correctly identified. The script tries to auto-detect it, but you can modify the `get_wifi_interface` method if needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the need to diagnose intermittent WiFi issues
- Built using Python's standard library tools