#!/usr/bin/env python3
"""
WiFi Network Monitor for macOS
------------------------------
Monitors WiFi connection quality over time and detects potential network glitches.
Collects metrics including:
- Signal strength (RSSI)
- Latency (ping times)
- Packet loss
- Connection status
- Transmission rates

Requirements:
- Python 3.6+
- macOS
- Root privileges for some operations (run with sudo)
"""

import subprocess
import re
import time
import datetime
import csv
import os
import signal
import statistics
import argparse
from typing import Dict, List, Tuple, Optional, Any

class WiFiMonitor:
    def __init__(self, 
                 duration_minutes: int = 60,
                 ping_interval: int = 5, 
                 ping_target: str = "8.8.8.8",
                 ping_count: int = 5,
                 output_file: str = "wifi_monitor_results.csv",
                 glitch_threshold_latency_ms: int = 100,
                 glitch_threshold_packet_loss: float = 10.0,
                 glitch_threshold_rssi_dbm: int = -70):
        """
        Initialize the WiFi monitor.
        
        Args:
            duration_minutes: Total monitoring duration in minutes
            ping_interval: Time between ping tests in seconds
            ping_target: IP address or hostname to ping
            ping_count: Number of pings to send in each test
            output_file: CSV file to save results
            glitch_threshold_latency_ms: Latency threshold (ms) to flag as a glitch
            glitch_threshold_packet_loss: Packet loss percentage to flag as a glitch
            glitch_threshold_rssi_dbm: RSSI value (dBm) below which to flag as a glitch
        """
        self.duration_seconds = duration_minutes * 60
        self.ping_interval = ping_interval
        self.ping_target = ping_target
        self.ping_count = ping_count
        self.output_file = output_file
        self.glitch_threshold_latency_ms = glitch_threshold_latency_ms
        self.glitch_threshold_packet_loss = glitch_threshold_packet_loss
        self.glitch_threshold_rssi_dbm = glitch_threshold_rssi_dbm
        self.results = []
        self.running = False
        self.start_time = None
        # Using wdutil instead of the deprecated airport utility
        self.wdutil_path = "/usr/bin/wdutil"
        
    def run_command(self, command: List[str]) -> Tuple[str, Optional[str]]:
        """Run a shell command and return stdout and stderr."""
        try:
            result = subprocess.run(command, 
                                    capture_output=True, 
                                    text=True, 
                                    check=False)
            return result.stdout, result.stderr
        except Exception as e:
            return "", str(e)
    
    def get_wifi_interface(self) -> str:
        """Get the name of the active WiFi interface."""
        stdout, _ = self.run_command(["networksetup", "-listallhardwareports"])
        wifi_section = re.search(r"Hardware Port: Wi-Fi.*?Device: (\w+)", stdout, re.DOTALL)
        if wifi_section:
            return wifi_section.group(1)
        return "en0"  # Default fallback
    
    def get_current_wifi_info(self) -> Dict[str, Any]:
        """Get current WiFi information including SSID, RSSI, and transmission rates using wdutil."""
        interface = self.get_wifi_interface()
        info = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ssid": "",
            "rssi_dbm": 0,
            "noise_dbm": 0,
            "tx_rate_mbps": 0,
            "connected": False
        }
        
        # First check if connected using networksetup
        stdout, _ = self.run_command(["networksetup", "-getairportnetwork", interface])
        ssid_match = re.search(r"Current Wi-Fi Network: (.*)", stdout)
        if ssid_match:
            info["ssid"] = ssid_match.group(1)
            info["connected"] = True
        
        # If not connected via the above method, try wdutil
        if not info["connected"]:
            stdout, _ = self.run_command(["sudo", self.wdutil_path, "info"])
            
            # Extract SSID from wdutil output
            ssid_match = re.search(r"SSID\s+: (\S+)", stdout)
            if ssid_match:
                info["ssid"] = ssid_match.group(1)
                info["connected"] = True
        
        # If connected, get more detailed WiFi information from wdutil
        if info["connected"]:
            stdout, _ = self.run_command(["sudo", self.wdutil_path, "info"])
            
            # Extract RSSI from wdutil output (look for RSSI or signal strength)
            rssi_match = re.search(r"RSSI\s+: ([-\d]+)", stdout)
            if rssi_match:
                info["rssi_dbm"] = int(rssi_match.group(1))
            else:
                # Alternative pattern for signal strength
                signal_match = re.search(r"Signal\s+: ([-\d]+)", stdout)
                if signal_match:
                    info["rssi_dbm"] = int(signal_match.group(1))
            
            # Extract noise from wdutil output
            noise_match = re.search(r"Noise\s+: ([-\d]+)", stdout)
            if noise_match:
                info["noise_dbm"] = int(noise_match.group(1))
            
            # Extract TX rate from wdutil output
            tx_rate_match = re.search(r"Tx Rate\s+: ([\d.]+)\s*Mbps", stdout)
            if tx_rate_match:
                info["tx_rate_mbps"] = float(tx_rate_match.group(1))
            else:
                # Alternative pattern for TX rate
                tx_rate_match = re.search(r"lastTxRate\s+: ([\d.]+)", stdout)
                if tx_rate_match:
                    info["tx_rate_mbps"] = float(tx_rate_match.group(1))
        
        return info
    
    def ping_test(self) -> Dict[str, Any]:
        """Perform a ping test and return results."""
        result = {
            "min_latency_ms": 0,
            "avg_latency_ms": 0,
            "max_latency_ms": 0,
            "stddev_latency_ms": 0,
            "packet_loss_percent": 0,
            "success": False
        }
        
        stdout, _ = self.run_command([
            "ping", 
            "-c", str(self.ping_count), 
            "-i", "0.2",  # 0.2 second interval between pings
            self.ping_target
        ])
        
        # Check if ping was successful
        if "--- " + self.ping_target + " ping statistics ---" not in stdout:
            return result
        
        # Extract packet loss
        packet_loss_match = re.search(r"(\d+\.?\d*)% packet loss", stdout)
        if packet_loss_match:
            result["packet_loss_percent"] = float(packet_loss_match.group(1))
        
        # Extract latency statistics
        latency_match = re.search(
            r"= (\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", stdout
        )
        if latency_match:
            result["min_latency_ms"] = float(latency_match.group(1))
            result["avg_latency_ms"] = float(latency_match.group(2))
            result["max_latency_ms"] = float(latency_match.group(3))
            result["stddev_latency_ms"] = float(latency_match.group(4))
            result["success"] = True
            
        return result
    
    def detect_glitches(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """Detect if current measurements indicate a network glitch."""
        glitches = {
            "latency_glitch": False,
            "packet_loss_glitch": False,
            "signal_strength_glitch": False,
            "connection_glitch": False,
            "any_glitch": False
        }
        
        # Check for latency glitch
        if data["ping_success"] and data["avg_latency_ms"] > self.glitch_threshold_latency_ms:
            glitches["latency_glitch"] = True
            
        # Check for packet loss glitch
        if data["packet_loss_percent"] > self.glitch_threshold_packet_loss:
            glitches["packet_loss_glitch"] = True
            
        # Check for signal strength glitch
        if data["rssi_dbm"] < self.glitch_threshold_rssi_dbm:
            glitches["signal_strength_glitch"] = True
            
        # Check for connection glitch
        if not data["connected"]:
            glitches["connection_glitch"] = True
            
        # Any glitch detected
        glitches["any_glitch"] = any([
            glitches["latency_glitch"],
            glitches["packet_loss_glitch"],
            glitches["signal_strength_glitch"],
            glitches["connection_glitch"]
        ])
        
        return glitches
    
    def collect_data_point(self) -> Dict[str, Any]:
        """Collect a single data point with all metrics."""
        wifi_info = self.get_current_wifi_info()
        ping_results = self.ping_test() if wifi_info["connected"] else {
            "min_latency_ms": 0,
            "avg_latency_ms": 0,
            "max_latency_ms": 0,
            "stddev_latency_ms": 0,
            "packet_loss_percent": 100,
            "success": False
        }
        
        data_point = {
            "timestamp": wifi_info["timestamp"],
            "ssid": wifi_info["ssid"],
            "connected": wifi_info["connected"],
            "rssi_dbm": wifi_info["rssi_dbm"],
            "noise_dbm": wifi_info["noise_dbm"],
            "tx_rate_mbps": wifi_info["tx_rate_mbps"],
            "ping_success": ping_results["success"],
            "min_latency_ms": ping_results["min_latency_ms"],
            "avg_latency_ms": ping_results["avg_latency_ms"],
            "max_latency_ms": ping_results["max_latency_ms"],
            "stddev_latency_ms": ping_results["stddev_latency_ms"],
            "packet_loss_percent": ping_results["packet_loss_percent"]
        }
        
        # Detect glitches
        glitches = self.detect_glitches(data_point)
        data_point.update(glitches)
        
        return data_point
    
    def save_to_csv(self):
        """Save results to CSV file."""
        if not self.results:
            return
            
        fieldnames = self.results[0].keys()
        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.results:
                writer.writerow(row)
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C to stop monitoring gracefully."""
        self.running = False
        print("\nStopping WiFi monitoring...")
    
    def start_monitoring(self):
        """Start monitoring WiFi for the specified duration."""
        self.running = True
        self.start_time = time.time()
        end_time = self.start_time + self.duration_seconds
        
        # Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print(f"WiFi Monitoring started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Monitoring for {self.duration_seconds//60} minutes, taking measurements every {self.ping_interval} seconds")
        print(f"Press Ctrl+C to stop monitoring early")
        print("-" * 80)
        
        interval_counter = 0
        
        try:
            while self.running and time.time() < end_time:
                current_time = time.time()
                elapsed_minutes = (current_time - self.start_time) / 60
                
                if interval_counter % 10 == 0:
                    print(f"\nTimestamp | SSID | RSSI | Latency | Loss | Glitch")
                    print(f"-" * 60)
                
                # Collect data point
                data_point = self.collect_data_point()
                self.results.append(data_point)
                
                # Pretty print current status
                glitch_indicator = "⚠️ " if data_point["any_glitch"] else "✓ "
                print(f"{data_point['timestamp']} | "
                      f"{data_point['ssid'][:15]:<15} | "
                      f"{data_point['rssi_dbm']:>4} dBm | "
                      f"{data_point['avg_latency_ms']:>5.1f} ms | "
                      f"{data_point['packet_loss_percent']:>3.0f}% | "
                      f"{glitch_indicator}")
                
                interval_counter += 1
                
                # Save results periodically
                if interval_counter % 12 == 0:
                    self.save_to_csv()
                    print(f"Results saved to {self.output_file}")
                
                # Wait until next interval
                next_time = current_time + self.ping_interval
                sleep_time = max(0, next_time - time.time())
                if sleep_time > 0 and self.running:
                    time.sleep(sleep_time)
        
        finally:
            # Save final results
            self.save_to_csv()
            
            # Generate summary
            self.generate_summary()
    
    def generate_summary(self):
        """Generate and print a summary of the monitoring session."""
        if not self.results:
            print("No data collected.")
            return
        
        total_samples = len(self.results)
        glitch_count = sum(1 for point in self.results if point["any_glitch"])
        glitch_percentage = (glitch_count / total_samples) * 100 if total_samples > 0 else 0
        
        connected_samples = sum(1 for point in self.results if point["connected"])
        connected_percentage = (connected_samples / total_samples) * 100 if total_samples > 0 else 0
        
        # Calculate averages
        connected_points = [point for point in self.results if point["connected"]]
        if connected_points:
            avg_rssi = statistics.mean(point["rssi_dbm"] for point in connected_points)
            
            ping_success_points = [point for point in self.results if point["ping_success"]]
            if ping_success_points:
                avg_latency = statistics.mean(point["avg_latency_ms"] for point in ping_success_points)
                avg_packet_loss = statistics.mean(point["packet_loss_percent"] for point in connected_points)
            else:
                avg_latency = 0
                avg_packet_loss = 100
        else:
            avg_rssi = 0
            avg_latency = 0
            avg_packet_loss = 100
        
        print("\n" + "=" * 80)
        print("WiFi Monitoring Summary")
        print("=" * 80)
        print(f"Monitoring period: {self.results[0]['timestamp']} to {self.results[-1]['timestamp']}")
        print(f"Total samples: {total_samples}")
        print(f"Connected percentage: {connected_percentage:.1f}%")
        print(f"Average RSSI: {avg_rssi:.1f} dBm")
        print(f"Average latency: {avg_latency:.1f} ms")
        print(f"Average packet loss: {avg_packet_loss:.1f}%")
        print(f"Glitches detected: {glitch_count} ({glitch_percentage:.1f}%)")
        print("=" * 80)
        print(f"Full results saved to: {self.output_file}")

def main():
    """Main function to parse arguments and start monitoring."""
    parser = argparse.ArgumentParser(description="Monitor WiFi network quality on macOS")
    parser.add_argument("-d", "--duration", type=int, default=60,
                        help="Monitoring duration in minutes (default: 60)")
    parser.add_argument("-i", "--interval", type=int, default=5,
                        help="Ping interval in seconds (default: 5)")
    parser.add_argument("-t", "--target", type=str, default="8.8.8.8",
                        help="Ping target (default: 8.8.8.8)")
    parser.add_argument("-o", "--output", type=str, default="wifi_monitor_results.csv",
                        help="Output CSV file (default: wifi_monitor_results.csv)")
    parser.add_argument("-l", "--latency-threshold", type=int, default=100,
                        help="Latency glitch threshold in ms (default: 100)")
    parser.add_argument("-p", "--packet-loss-threshold", type=float, default=10.0,
                        help="Packet loss glitch threshold in percent (default: 10.0)")
    parser.add_argument("-r", "--rssi-threshold", type=int, default=-70,
                        help="RSSI glitch threshold in dBm (default: -70)")
    args = parser.parse_args()
    
    # Emphasize that root privileges are required due to wdutil
    if os.geteuid() != 0:
        print("WARNING: This WiFi monitor requires root privileges to use wdutil.")
        print("Please run this script with sudo for full functionality.")
        proceed = input("Continue anyway? (y/n): ")
        if proceed.lower() != "y":
            return
    
    monitor = WiFiMonitor(
        duration_minutes=args.duration,
        ping_interval=args.interval,
        ping_target=args.target,
        output_file=args.output,
        glitch_threshold_latency_ms=args.latency_threshold,
        glitch_threshold_packet_loss=args.packet_loss_threshold,
        glitch_threshold_rssi_dbm=args.rssi_threshold
    )
    
    monitor.start_monitoring()

if __name__ == "__main__":
    main()