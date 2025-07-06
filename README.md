# RF Cover Time Based for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://hacs.xyz)

The **RF Cover Time Based** integration for Home Assistant allows you to create a `cover` entity that intelligently calculates its position based on travel time. It is designed to control RF (Radio Frequency) or IR (Infrared) controlled covers, blinds, shutters, or awnings by sending commands through an existing Home Assistant `remote` entity (like Broadlink, Tuya, or any other remote platform).

This component does not communicate with a physical device directly. Instead, it acts as a smart layer on top of your remote, giving you a fully functional cover entity with position control, even for devices that don't report their state.

## Features

-   **UI Configuration**: Fully configurable through the Home Assistant user interface. No YAML required.
-   **Position Control**: Supports `open`, `close`, `stop`, and `set_position`.
-   **State Restoration**: Remembers its position after a Home Assistant restart.
-   **Assumed State**: Accurately reflects in the UI that the position is calculated, not confirmed by the device.
-   **Universal Remote Support**: Works with any integration that provides a `remote` entity.
-   **Device Class Support**: Correctly handles different cover types, including `awning`, where open/close logic is inverted.

## Prerequisites

You **must** have a working `remote` entity already configured in Home Assistant. This integration sends commands *through* that entity.

Common integrations that provide `remote` entities include:
-   Broadlink
-   Tuya
-   Xiaomi Miio

Before you begin, make sure you know the entity ID of your remote (e.g., `remote.broadlink_rm_pro`) and the specific commands needed to open, close, and stop your cover.

## Installation

### Method 1: HACS (Recommended)

1.  Ensure you have HACS (Home Assistant Community Store) installed.
2.  In HACS, go to `Integrations`.
3.  Click the three dots in the top right corner and select `Custom repositories`.
4.  In the `Repository` field, paste the URL of this GitHub repository: `https://github.com/edufabra/rf_cover_time_based`.
5.  Select `Integration` for the category and click `Add`.
6.  The "RF Cover Time Based" integration will now appear in the HACS list. Click `Install`.
7.  Restart Home Assistant.

### Method 2: Manual Installation

1.  Download the latest release from the Releases page.
2.  Unzip the downloaded file.
3.  Copy the `rf_cover_time_based` directory into the `custom_components` directory of your Home Assistant configuration folder. If the `custom_components` directory does not exist, you need to create it.
4.  Your directory structure should look like this:
    
```
/config/
├── custom_components/
│   └── rf_cover_time_based/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── manifest.json
│       ├── const.py
│       ├── translations/
│       │   └── en.json
│       │   └── ... (other translations)
│       └── ... (other files)
├── configuration.yaml
└── ... (other config files)
```
5. Restart Home Assistant.

## Configuration

Once installed, you can add and configure your cover from the Home Assistant UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click the **+ Add Integration** button in the bottom right corner.
3.  Search for **"RF Cover Time Based"** and select it.
4.  A configuration dialog will appear. Fill in the following fields:
    -   **Name**: A friendly name for your cover (e.g., "Living Room Blinds"). This will be used to create the entity name.
    -   **Remote Entity**: Select the `remote` entity from the dropdown list that will be used to send the commands.
    -   **Open Command**: The exact command string to send to the remote entity to open the cover.
    -   **Close Command**: The command string to send to close the cover.
    -   **Stop Command**: The command string to send to stop the cover's movement.
    -   **Travel Time Down (seconds)**: The time, in seconds, it takes for the cover to go from fully open (100%) to fully closed (0%).
    -   **Travel Time Up (seconds)**: The time, in seconds, it takes for the cover to go from fully closed (0%) to fully open (100%).
    -   **Device Class**: Select the type of cover you are controlling (e.g., `Shutter`, `Blind`, `Awning`). This affects the icon and behavior.
5.  Click **Submit**. A new cover entity will be created and ready to use in your dashboards and automations.

## Changing Settings (Options Flow)

If you need to adjust the travel times or other settings after the initial setup:
1.  Go to **Settings** > **Devices & Services**.
2.  Find the "RF Cover Time Based" integration entry you wish to change.
3.  Click **Configure**.
4.  You will be presented with the same form, where you can update the values as needed.

## Acknowledgements
This integration is heavily inspired by the original work of [nagyrobi/home-assistant-custom-components-cover-rf-time-based](https://github.com/nagyrobi/home-assistant-custom-components-cover-rf-time-based). That project, which is now archived and unmaintained, served as the foundation for creating this modern version, which is fully configurable through the UI and adapted to the current Home Assistant architecture.

