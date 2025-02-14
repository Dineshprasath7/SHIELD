import re
import time
from collections import defaultdict
import logging
import tkinter as tk
from tkinter import messagebox
import sys
import socket
import select
import random
import hashlib
import psutil  # For dynamic CPU and memory usage
from collections import defaultdict
import logging
import time
import threading
import json

#Strategic Host Intrusion Elimination and Load Distribution
DEFAULT_SERVER_POOL = [('127.0.0.1', 7777), ('127.0.0.1', 8888), ('127.0.0.1', 9999)]
DEFAULT_SERVER_WEIGHTS = {('127.0.0.1', 7777): 2, ('127.0.0.1', 8888): 1, ('127.0.0.1', 9999): 1}
ACTIVE_CONNECTIONS = defaultdict(int)
OVERLOAD_THRESHOLD = 5  # Max connections before a server is considered overloaded
REQUEST_LIMIT_PER_IP = 100  # Limit requests from a single IP address
CONNECTION_TIMEOUT = 60  # Timeout for idle connections (in seconds)

# Configure logging (corrected)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class PacketAnalyzer:
    """Intrusion Detection System for analyzing incoming packets."""

    def __init__(self, max_packet_size=4096, signature_db=None):
        self.max_packet_size = max_packet_size
        self.repetitive_requests = defaultdict(lambda: {"count": 0, "timestamp": time.time()})
        self.signature_db = signature_db or self.load_signature_database()

        # Time window for repetitive request checking (in seconds)
        self.time_window = 60
        self.request_limit = 100  # Max allowed requests per IP within time window

        # Alert counters for attack types
        self.alert_counters = defaultdict(int)

        # GUI-related attributes for notifications
        self.root = tk.Tk()  # Create a hidden Tkinter root for messagebox popups
        self.root.withdraw()  # Hide the root window since we only want pop-ups

    def load_signature_database(self):
        """Load a simple signature database with predefined malicious patterns."""
        return [
            {"name": "SQL Injection", "pattern": r"(\%27)|(\')|(\-\-)|(\%23)|(#)", "description": "SQL Injection Attempt"},
            {"name": "XSS", "pattern": r"(<script>)", "description": "Cross-Site Scripting Attempt"},
            {"name": "Command Injection", "pattern": r"(\;|\&\&|\|\|)", "description": "Command Injection Attempt"},
            {"name": "Path Traversal", "pattern": r"(\.\.)", "description": "Path Traversal Attempt"},
            {"name": "Malicious File Upload", "pattern": r"(\.php|\.exe|\.sh)", "description": "Potential Malicious File Upload"},
        ]

    def analyze_packet(self, data, client_ip):
        """Analyze packet for anomalies, flooding, and known attack patterns."""
        alerts = []

        # Packet size analysis
        if len(data) > self.max_packet_size:
            alerts.append(f"Packet from {client_ip} exceeds max size! Size: {len(data)}")
            self.send_notification(f"Alert: Packet from {client_ip} exceeds max size! Size: {len(data)}")

        # Check for repetitive requests (potential DoS attack)
        current_time = time.time()
        request_info = self.repetitive_requests[client_ip]
        request_info["count"] += 1
        request_info["timestamp"] = current_time

        if request_info["count"] > self.request_limit:
            alerts.append(f"DoS attack suspected from {client_ip}: too many requests.")
            self.send_notification(f"Alert: DoS attack suspected from {client_ip}: too many requests.")

        # Check for known attack signatures
        for signature in self.signature_db:
            if re.search(signature["pattern"], data.decode("utf-8", errors="ignore")):
                alerts.append(f"{signature['name']} detected from {client_ip}: {signature['description']}")
                self.send_notification(f"Alert: {signature['name']} detected from {client_ip}: {signature['description']}")
                self.alert_counters[signature["name"]] += 1  # Update alert counter

        return alerts

    def send_notification(self, message):
        """Send a notification via GUI pop-up."""
        logging.warning(message)
        # Pop-up window to show the notification
        messagebox.showwarning("Alert", message)  # Pop-up notification window

    def simulate_packet_analysis(self, client_ip, packet_data):
        """Method to be used in GUI mode for analyzing packets entered by the user."""
        return self.analyze_packet(packet_data.encode("utf-8", errors="ignore"), client_ip)


def main():
    """Main function to test the PacketAnalyzer with pop-up notifications."""
    analyzer = PacketAnalyzer(max_packet_size=1024)  # Smaller max packet size for testing

    print("\nPacket Analyzer Testing with Notifications")
    print("------------------------------------------")

    while True:
        print("\nChoose a test case:")
        print("1. SQL Injection Test")
        print("2. XSS Test")
        print("3. Oversized Packet Test")
        print("4. DoS Attack Test")
        print("5. Custom Packet Test")
        print("0. Exit")

        choice = input("Enter your choice: ")

        if choice == "0":
            break
        elif choice == "1":
            client_ip = '192.168.1.100'
            sql_payload = "SELECT * FROM users WHERE username='admin' --"
            alerts = analyzer.analyze_packet(sql_payload.encode(), client_ip)
            print("Alerts:", alerts)
        elif choice == "2":
            client_ip = '192.168.1.101'
            xss_payload = "<script>alert('XSS')</script>"
            alerts = analyzer.analyze_packet(xss_payload.encode(), client_ip)
            print("Alerts:", alerts)
        elif choice == "3":
            client_ip = '192.168.1.102'
            oversized_payload = "A" * 2048  # Payload larger than max_packet_size
            alerts = analyzer.analyze_packet(oversized_payload.encode(), client_ip)
            print("Alerts:", alerts)
        elif choice == "4":
            client_ip = '192.168.1.103'
            dos_payload = "GET /index.html"
            for _ in range(101):  # Exceed the request limit
                alerts = analyzer.analyze_packet(dos_payload.encode(), client_ip)
            print("Alerts:", alerts)
        elif choice == "5":
            client_ip = input("Enter the client IP: ")
            packet_data = input("Enter the packet data: ")
            alerts = analyzer.analyze_packet(packet_data.encode(), client_ip)
            print("Alerts:", alerts)
        else:
            print("Invalid choice, please try again.")

    print("\nExiting Packet Analyzer.")
    analyzer.root.quit()  # Close the Tkinter GUI cleanly


ip_request_count = defaultdict(lambda: {"count": 0, "timestamp": time.time()})

def least_connections():
    """Select the server with the least connections."""
    return min(DEFAULT_SERVER_POOL, key=lambda server: ACTIVE_CONNECTIONS[server])

def round_robin():
    """Round robin server selection."""
    round_robin.counter = (round_robin.counter + 1) % len(DEFAULT_SERVER_POOL)
    return DEFAULT_SERVER_POOL[round_robin.counter]

# Initialize round robin counter
round_robin.counter = -1

def ip_hashing(client_ip):
    """Select a server based on the hashed client IP."""
    hashed_ip = int(hashlib.sha2(client_ip.encode()).hexdigest(), 16)
    return DEFAULT_SERVER_POOL[hashed_ip % len(DEFAULT_SERVER_POOL)]

def weighted_round_robin(weights):
    """Weighted round robin server selection."""
    total_weight = sum(weights.values())
    cumulative_weights = []
    cumulative_sum = 0

    for server, weight in weights.items():
        cumulative_sum += weight
        cumulative_weights.append((server, cumulative_sum))

    random_choice = random.uniform(0, total_weight)
    for server, cumulative_weight in cumulative_weights:
        if random_choice <= cumulative_weight:
            return server

class LoadBalancer:
    flow_map = dict()
    socket_list = list()
    statistics = {"total_requests": 0, "total_response_time": 0}
    health_check_log = []

    def __init__(self, ip, port,algo='weighted round robin', config_file=None):
        self.ip = ip
        self.port = port
        self.algorithm = algo
        print(algo)
        self.weights = DEFAULT_SERVER_WEIGHTS.copy()
        self.packet_analyzer = PacketAnalyzer(max_packet_size=4096)
        # Load configuration if a config file is provided
        if config_file:
            self.load_config(config_file)
        else:
            self.SERVER_POOL = DEFAULT_SERVER_POOL

        self.client_side_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_side_socket.bind((self.ip, self.port))
        self.client_side_socket.listen()
        self.socket_list.append(self.client_side_socket)

        logging.info(f"LoadBalancer initialized on {self.ip}:{self.port} with algorithm '{self.algorithm}'")
        
        # Start a separate thread for health checks
        self.running = True
        self.health_check_interval = 30  # seconds
        self.health_check_thread = threading.Thread(target=self.start_health_check)
        self.health_check_thread.start()

    def load_config(self, config_file):
        """Load server configurations from a JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.SERVER_POOL = config.get('servers', DEFAULT_SERVER_POOL)
                self.weights = config.get('weights', DEFAULT_SERVER_WEIGHTS)
                logging.info("Configuration loaded from JSON.")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")

    def start_health_check(self):
        """Periodically check the health of servers."""
        while self.running:
            self.check_health()
            time.sleep(self.health_check_interval)

    def start(self):
        """Start the load balancer and handle incoming connections."""
        logging.info("LoadBalancer is now running.")
        while True:
            readable, writable, error = select.select(self.socket_list, [], [])
            for sock in readable:
                if sock == self.client_side_socket:
                    # Accept new client connections
                    self.conn_accept()
                else:
                    # Handle incoming data from clients or servers
                    try:
                        data = sock.recv(4096)  # Increased buffer size for requests
                        if data:
                            self.data_recv(sock, data)
                        else:
                            self.conn_close(sock)
                    except Exception as e:
                        logging.error(f"Error receiving data: {e}")
                        self.conn_close(sock)

    def conn_accept(self):
        """Accept a new client connection and route to a server."""
        client_socket, client_addr = self.client_side_socket.accept()
        logging.info(f'Client connected {client_addr} <=========> {self.client_side_socket.getsockname()}')
        
        # Check rate limit for the client IP
        if self.rate_limit_exceeded(client_addr[0]):
            logging.warning(f'Rate limit exceeded for IP: {client_addr[0]}')
            client_socket.close()
            return
        
        server_ip, server_port = self.select_server(self.SERVER_POOL, self.algorithm, client_addr[0])
        logging.info(f'Forwarding to server {server_ip}:{server_port}')
        
        server_side_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_side_socket.connect((server_ip, server_port))
            logging.info(f'Server side socket {server_side_socket.getsockname()} Initiated')
            logging.info(f'Server Connected {server_side_socket.getsockname()} <======> {server_ip}:{server_port}')
            ACTIVE_CONNECTIONS[(server_ip, server_port)] += 1
        except Exception as e:
            logging.error(f'Cannot connect with remote server err: {e}')
            logging.info(f'Closing connection with the client {client_addr}')
            client_socket.close()
            return
        
        # Update the flow map
        self.flow_map[client_socket] = server_side_socket
        self.flow_map[server_side_socket] = client_socket
        self.socket_list.append(server_side_socket)
        self.socket_list.append(client_socket)

    def data_recv(self, sock, data):
        """Receive data from clients and forward it to the appropriate server."""
        logging.info(f'Receiving packets {sock.getpeername()} <=====> {sock.getsockname()} and data: {data}')
        remote_socket = self.flow_map.get(sock)

        if remote_socket is None:
            logging.error(f'No remote socket found for {sock.getpeername()}')
            return

        # Extract the client's IP address from the socket
        client_ip = sock.getpeername()[0]

        # Analyze the packet for potential threats
        alerts = self.packet_analyzer.analyze_packet(data, client_ip)

        # Display alerts, if any
        if alerts:
            logging.info(f'Alerts detected: {alerts}')

        start_time = time.time()  # Start timing for response
        try:
            # Log the request
            logging.info(f'Forwarding request to {remote_socket.getpeername()}')
            remote_socket.send(data)
            logging.info(f'Sent data to server {remote_socket.getpeername()}')

            while True:
                response = remote_socket.recv(4096)
                if not response:
                    break  # No more data from the server
                sock.send(response)
                logging.info(f'Sent response back to client {sock.getpeername()}')

            # Update statistics
            response_time = time.time() - start_time
            self.statistics['total_requests'] += 1
            self.statistics['total_response_time'] += response_time
            logging.info(f'Response time: {response_time:.4f} seconds')
        except OSError as e:
            logging.error(f'Error during data transfer: {e}')
            self.conn_close(sock)
        finally:
            # Ensure that we close the remote socket if it was valid
            if remote_socket in self.socket_list:
                self.socket_list.remove(remote_socket)
                remote_socket.close()


    def conn_close(self, sock):
        """Close the client and server sockets."""
        try:
            logging.info(f'Client {sock.getpeername()} has disconnected')
        except OSError as e:
            logging.error(f'Error getting peername for socket: {e}')
            return  # Exit if we cannot get the peername

        # Get the remote socket associated with this client socket
        ss_socket = self.flow_map.get(sock)

        # Safely close the remote socket
        if ss_socket is not None:
            if ss_socket in self.socket_list:
                self.socket_list.remove(ss_socket)
                logging.info(f'Removed server socket {ss_socket.getpeername()} from socket list')
                ss_socket.close()  # Close the remote socket

        # Safely close the client socket
        if sock in self.socket_list:
            self.socket_list.remove(sock)
            logging.info(f'Removed client socket {sock.getpeername()} from socket list')
        sock.close()

        # Clean up the flow map
        if sock in self.flow_map:
            del self.flow_map[sock]


    def select_server(self, servers, algorithm, client_ip=None):
        """Select a server based on the chosen load balancing algorithm."""
        if algorithm == "random":
            return random.choice(servers)
        if algorithm == "least connection":
            return least_connections()
        if algorithm == "round robin":
            return round_robin()
        if algorithm == "ip hashing" and client_ip:
            return ip_hashing(client_ip)
        if algorithm == "weighted round robin":
            return weighted_round_robin(self.weights)
        if algorithm == "cpu based":
            return self.cpu_based_balancing()
        if algorithm == "memory based":
            return self.memory_based_balancing()

    def cpu_based_balancing(self):
        """Return the server with the lowest CPU usage."""
        server_cpu_usage = [(server, psutil.cpu_percent(interval=1)) for server in DEFAULT_SERVER_POOL]
        return min(server_cpu_usage, key=lambda x: x[1])[0]

    def memory_based_balancing(self):
        """Return the server with the lowest memory usage."""
        server_memory_usage = [(server, psutil.virtual_memory().percent) for server in DEFAULT_SERVER_POOL]
        return min(server_memory_usage, key=lambda x: x[1])[0]

    def rate_limit_exceeded(self, client_ip):
        """Check if the request limit for the client IP has been exceeded."""
        request_info = ip_request_count[client_ip]
        current_time = time.time()

        # Reset the count if the time exceeds REQUEST_LIMIT_PERIOD (1 hour)
        if current_time - request_info["timestamp"] > 3600:
            request_info["count"] = 0
            request_info["timestamp"] = current_time
        
        # Check if limit exceeded
        if request_info["count"] >= REQUEST_LIMIT_PER_IP:
            return True
        
        # Increment the count
        request_info["count"] += 1
        return False

    def check_health(self):
        """Check the health of each server in the pool."""
        for server in DEFAULT_SERVER_POOL:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)  # Set a short timeout for health checks
                    s.connect(server)
                    self.health_check_log.append((server, True))
                    logging.info(f'Server {server} is healthy.')
            except Exception as e:
                self.health_check_log.append((server, False))
                logging.warning(f'Server {server} is not reachable: {e}')

if __name__ == "__main__":
    if len(sys.argv) <3:
        print("Usage: python load_balancer.py <IP_ADDRESS> <PORT>")
        sys.exit(1)

    ip_address = sys.argv[1]
    port = int(sys.argv[2])
    algorithm = sys.argv[3]
    lb = LoadBalancer(ip_address, port,algorithm)
    lb.start()
