# Tech Recuperation (Wanas) - Home Assistant Custom Integration

Custom Home Assistant integration for Wanas recuperation units controlled through Tech Controllers eMODUL cloud API (ST-340 V2).

## What Is Implemented

- Config flow login using eMODUL email/password.
- Module discovery and selection when multiple modules are available.
- Cloud polling coordinator (`iot_class: cloud_polling`).
- Entities:
  - Sensors: current gear, known temperature sensors, heat recovery efficiency.
  - Switch: recuperation on/off.
  - Select: temporary gear override.
  - Number: party mode duration, recuperation parameter.
  - Buttons: party mode trigger, restore today's backed-up schedule.
- Services for schedule and gear control:
  - `tech_recuperation.set_day_schedule`
  - `tech_recuperation.set_gear_now`
  - `tech_recuperation.set_gear_until`
  - `tech_recuperation.restore_day_schedule`
- Schedule backup/restore protection:
  - Original day schedule is backed up before override.
  - Backup is persisted on disk using Home Assistant `Store`.
  - Restore writes backup back to API and clears persisted backup.

## Requirements

- Home Assistant with support for custom integrations.
- A valid eMODUL account linked to your controller.
- Internet connectivity (integration uses cloud API).

## Installation

### Option A: Manual install

1. Copy this folder to your Home Assistant config directory:

```text
<config>/custom_components/tech_recuperation/
```

2. Restart Home Assistant.
3. Go to `Settings -> Devices & Services -> Add Integration`.
4. Search for `Tech Recuperation (Wanas)`.
5. Enter eMODUL credentials and select module when prompted.

### Option B: Git checkout in HA config

If you manage HA config with git, place this repository content so the integration lands at:

```text
custom_components/tech_recuperation/
```

Then restart Home Assistant and add the integration via UI.

## Configuration Notes

- YAML configuration is not required; setup is via UI config flow.
- Polling interval is currently 30 seconds.
- Day IDs in API are `0=Sunday ... 6=Saturday`; helper conversion from Python weekday is already handled internally.

## Service Usage

Use Developer Tools -> Actions in Home Assistant, or call from automations/scripts.

### 1) Set full day schedule

Service: `tech_recuperation.set_day_schedule`

Example:

```yaml
action: tech_recuperation.set_day_schedule
data:
  day: monday
  slots:
    - { start: "00:00", end: "06:00", gear: 1, temp: 20 }
    - { start: "06:00", end: "10:00", gear: 2, temp: 21 }
    - { start: "10:00", end: "16:00", gear: 1, temp: 20 }
    - { start: "16:00", end: "22:00", gear: 2, temp: 21 }
    - { start: "22:00", end: "23:59", gear: 1, temp: 20 }
```

Rules for `slots`:

- Exactly 5 slots.
- Must be contiguous.
- Must fully cover `00:00` to `23:59`.
- `gear` must be `0..3` (`off`, `gear_1`, `gear_2`, `gear_3`).
- `temp` must be `10..30`.

### 2) Set gear from now to end of day

Service: `tech_recuperation.set_gear_now`

```yaml
action: tech_recuperation.set_gear_now
data:
  day: today
  gear: gear_3
  temp: 22
```

### 3) Set gear from now until specific time

Service: `tech_recuperation.set_gear_until`

```yaml
action: tech_recuperation.set_gear_until
data:
  day: today
  gear: gear_3
  until: "22:00"
  temp: 22
  revert_gear: gear_1
```

### 4) Restore backed-up day schedule

Service: `tech_recuperation.restore_day_schedule`

```yaml
action: tech_recuperation.restore_day_schedule
data:
  day: today
```

This restores the last backup for that day (if present).

## Example Automations

### Boost ventilation when humidity rises

```yaml
alias: Ventilation boost on high humidity
triggers:
  - trigger: numeric_state
    entity_id: sensor.bathroom_humidity
    above: 70
actions:
  - action: tech_recuperation.set_gear_until
    data:
      day: today
      gear: gear_3
      until: "23:00"
      revert_gear: gear_1
mode: single
```

### Restore schedule after humidity drops

```yaml
alias: Restore ventilation schedule after shower
triggers:
  - trigger: numeric_state
    entity_id: sensor.bathroom_humidity
    below: 60
conditions:
  - condition: state
    entity_id: input_boolean.ventilation_boost_active
    state: "on"
actions:
  - action: tech_recuperation.restore_day_schedule
    data:
      day: today
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.ventilation_boost_active
mode: single
```

Use this pattern together with a "boost start" automation that sets
`input_boolean.ventilation_boost_active` to `on` when `set_gear_now` or
`set_gear_until` is triggered. This way restore is only called when an override
actually happened.

## Development and Local Test Workflow

From repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest pytest-asyncio voluptuous
.venv/bin/python -m pytest tests
```

Current suite includes tests for helpers, coordinator, entities, API layer, sensors, and config flow.

## Build / Packaging

This integration is Python-only and has no separate compile/build step.

For deployment/package creation, you can archive just the integration directory:

```bash
zip -r tech_recuperation.zip custom_components/tech_recuperation
```

Then unpack it into your HA config under `custom_components/`.

## Troubleshooting

- `invalid_auth` during setup: verify eMODUL credentials.
- `cannot_connect`: check internet connectivity and eMODUL availability.
- Restore button unavailable: no backup exists for today yet.
- IDE import errors for `homeassistant.*`: expected outside full HA dev environment.

## Known Scope / Limitations

- Cloud dependency: no local/offline controller API support.
- Service schemas allow flexible values, but runtime validation enforces ranges and schedule shape.
- Integration targets ST-340 V2/eMODUL behavior and day-element mapping known for this controller family.

## Security

- **Credential storage**: Your eMODUL username, password, and API token are stored in Home Assistant config entries (`.storage/core.config_entries` on disk). This is the standard mechanism used by HA integrations and is not additionally encrypted at rest.
- **Do not share** HA backups, `.storage` files, or diagnostic logs publicly without reviewing them for credentials first.
- **Logging**: This integration never intentionally logs passwords, tokens, or authorization headers. API error responses are truncated and exception messages are sanitized to avoid leaking sensitive data in log files.
- **Transport**: All API communication uses HTTPS to the eMODUL cloud endpoint.
