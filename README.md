>[!CAUTION]
> This project is currently under heavy development. Expect rapid changes and evolving features!

<h1 align="center">Nexus LED Scoreboard</h1>
<br>
<p align="center">
    <a href="https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/peteywhit/nexus-led-scoreboard/ci.yml?branch=dev&label=Dev+CI&style=for-the-badge&logo=github"/></a>
    &nbsp;&nbsp;<a href="https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/peteywhit/nexus-led-scoreboard/ci.yml?branch=main&label=Main+CI&style=for-the-badge&logo=github"/></a>
    <br><br>
    <a href="https://github.com/peteywhit/nexus-led-scoreboard/blob/main/LICENSE"><img src="https://img.shields.io/github/license/peteywhit/nexus-led-scoreboard?style=for-the-badge"/></a>
    &nbsp;&nbsp;<a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white"/></a>
    <br><br>
    <a href="https://buymeacoffee.com/peteywhit"><img src="https://img.shields.io/badge/-buy_me_a_coke-%23FFDD00?style=for-the-badge&logo=coca-cola&logoSize=auto&logoColor=black"/></a>
</p>

<!--[![Dev CI - dev Branch](https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml/badge.svg?branch=dev&label=Dev+CI&style=for-the-badge)](https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml)
[![Main CI - main Branch](https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml/badge.svg?branch=main&label=Main+CI&style=for-the-badge)](https://github.com/peteywhit/nexus-led-scoreboard/actions/workflows/ci.yml)
[![GitHub release (latest)](https://img.shields.io/github/v/release/peteywhit/nexus-led-scoreboard)](https://github.com/peteywhit/nexus-led-scoreboard/releases/latest)
[![Top Language](https://img.shields.io/github/languages/top/peteywhit/nexus-led-scoreboard)](https://github.com/peteywhit/nexus-led-scoreboard)
[![License](https://img.shields.io/github/license/peteywhit/nexus-led-scoreboard?style=for-the-badge)](https://github.com/peteywhit/nexus-led-scoreboard/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/peteywhit/nexus-led-scoreboard?style=social)](https://github.com/peteywhit/nexus-led-scoreboard/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/peteywhit/nexus-led-scoreboard?style=social)](https://github.com/peteywhit/nexus-led-scoreboard/network/members)-->


---

## 🚀 Project Overview

Welcome to the **Nexus LED Scoreboard** project! 🎉 This ambitious endeavor aims to create a dynamic, multi-sport LED scoreboard system that brings real-time scores and game information right into your home or fan cave. Imagine never missing a moment, with live updates glowing on a customizable LED matrix display.

Built with Python, this project is designed for versatility, interfacing with various sports APIs to fetch up-to-the-minute data and controlling LED matrices (like those powered by Raspberry Pi) for stunning visual output.

### Why Nexus LED Scoreboard?
* **Beyond a Single Sport:** Unlike existing solutions, we're building for *all* your favorite sports! 🏈🏀⚾⚽🏒
* **Real-time Immersion:** Get the latest scores as they happen, no refreshing needed.
* **DIY Spirit:** Perfect for hobbyists and makers who love building their own smart devices.

---

## ✨ Features (Planned & In Progress)

* **Multi-Sport Support:** Initial focus on major leagues (MLB, NHL, NBA, NFL, Soccer), with an extensible architecture for more.
* **Real-time Score Updates:** Fetching live game data from reliable sports APIs.
* **Customizable Display Layouts:** Options to tailor how scores, time, and other data are presented on the LED matrix.
* **Modular Architecture:** Designed with separate components for data fetching, rendering, and hardware control, making it easy to extend and maintain.
* **Event Notifications:** (Future) Potentially flash lights or show special animations for key game events (e.g., scores, home runs).

---

## 🛠️ Technology Stack

* **Primary Language:** Python 🐍
* **Hardware Interface:** `rpi-rgb-led-matrix` (or similar libraries for LED control)
* **Data Fetching:** Various open-source and official sports APIs (e.g., `MLB-StatsAPI`, others to be integrated)
* **System:** Primarily designed for Raspberry Pi OS

---

## 🚀 Getting Started

This section will guide you through setting up your own Nexus LED Scoreboard.

### Prerequisites
* A Raspberry Pi (or compatible single-board computer) 🥧
* A compatible LED matrix panel (e.g., Adafruit RGB Matrix Panel)
* Python 3.8+ installed
* Basic understanding of command line operations

### Hardware Setup (for Raspberry Pi LED Matrix)
The `rpi-rgb-led-matrix` library, essential for driving the LED panels, requires specific compilation on a Raspberry Pi.
**Note:** This library cannot be installed directly via `pip` on standard development machines (like your Windows PC or GitHub Actions runners) as it's tightly coupled to Raspberry Pi's GPIO.

**On your Raspberry Pi, follow these steps:**
1.  **Update your system:**
    ```bash
    sudo apt update && sudo apt upgrade
    ```
2.  **Install build tools and Python development headers:**
    ```bash
    sudo apt install -y python3-dev libatlas-base-dev git
    ```
3.  **Clone and build `rpi-rgb-led-matrix`:**
    ```bash
    git clone [https://github.com/hzeller/rpi-rgb-led-matrix.git](https://github.com/hzeller/rpi-rgb-led-matrix.git)
    cd rpi-rgb-led-matrix
    make build-python PYTHON=$(which python3) # Or specify your Python version
    sudo make install-python PYTHON=$(which python3)
    ```
    *(This assumes you'll build and install it globally or within a Pi-specific virtual environment.)*

### Initial Setup (Local Development)

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/peteywhit/nexus-led-scoreboard.git](https://github.com/peteywhit/nexus-led-scoreboard.git)
    cd nexus-led-scoreboard
    ```
2.  **Set up your Python Virtual Environment (Highly Recommended!):**
    ```bash
    python -m venv .venv
    # On Windows:
    .\.venv\Scripts\activate
    # On macOS/Linux:
    source ./.venv/bin/activate
    ```
3.  **Install development dependencies and your project in editable mode:**
    ```bash
    pip install -e . # Installs your project for development
    pip install ruff pytest pytest-cov # Essential tools for linting and testing
    ```
4.  **Run initial checks:**
    ```bash
    ruff check .
    ruff format .
    pytest
    ```
---
### Running for Development

Once you have completed the [Prerequisites](#prerequisites) and [Hardware Setup](#hardware-setup-for-raspberry-pi-led-matrix) (if applicable), you can run the Nexus LED Scoreboard application.

Make sure your Python virtual environment is activated. From the project's root directory, execute the main application module:

```bash
python -m nexus_led_scoreboard.main
```
---
### Deployment on Raspberry Pi

For running the Nexus LED Scoreboard application on a dedicated Raspberry Pi, the setup involves preparing the hardware-specific library and then installing the application as a system-wide package or within a dedicated virtual environment on the Pi.

**Before Deployment:**

Ensure you have followed the [Hardware Setup (for Raspberry Pi LED Matrix)](#hardware-setup-for-raspberry-pi-led-matrix) instructions on your Raspberry Pi. This is critical for the `rpi-rgb-led-matrix` library to be available.

**Deployment Steps:**

1.  **Clone the Repository on your Raspberry Pi:**
    If you haven't already, clone the project directly onto your Raspberry Pi:
    ```bash
    git clone [https://github.com/peteywhit/nexus-led-scoreboard.git](https://github.com/peteywhit/nexus-led-scoreboard.git)
    cd nexus-led-scoreboard
    ```

2.  **(Recommended) Create a Dedicated Virtual Environment (on Pi):**
    It's good practice to install your application and its dependencies into a virtual environment even on the Pi, to avoid conflicts with system-wide Python packages.
    ```bash
    python3 -m venv venv_scoreboard
    source venv_scoreboard/bin/activate
    ```

3.  **Install the Nexus LED Scoreboard Application:**
    While inside the `nexus-led-scoreboard` directory and with your virtual environment activated (if you created one), install the application:
    ```bash
    pip install .
    ```
    This command installs your `nexus-led-scoreboard` package and its pure Python dependencies (like `requests`) into the active environment. It relies on the `rpi-rgb-led-matrix` library already being compiled and installed on the system as per the Hardware Setup.

4.  **Run the Installed Application:**
    After installation, you can run the application. We will define a simple console script entry point in a future step to make this even easier (e.g., `nexus-scoreboard`), but for now, you can run it as:
    ```bash
    python -m nexus_led_scoreboard.main
    ```
    *(In a production setup, you would typically configure this to run automatically at boot using a system service like `systemd`.)*