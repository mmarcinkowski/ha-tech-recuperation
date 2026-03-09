"""Unit tests for sensor entities."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.tech_recuperation.sensor import (
    CurrentGearSensor,
    HeatRecoveryEfficiencySensor,
    TemperatureTileSensor,
    TemperatureWidgetSensor,
)


def test_temperature_tile_sensor_reads_and_scales_value() -> None:
    """Tile sensor reads raw value and converts to degrees."""
    coordinator = SimpleNamespace(
        data={"tiles": {1: {"params": {"txtId": 795, "value": 215}}}},
    )
    sensor = TemperatureTileSensor(coordinator, "module-1", 795)
    assert sensor.native_value == 21.5


def test_temperature_widget_sensor_reads_widget_value() -> None:
    """Widget sensor reads nested widget value and converts to degrees."""
    coordinator = SimpleNamespace(
        data={
            "tiles": {
                1: {
                    "params": {
                        "widget1": {"txtId": 1840, "value": 205},
                        "widget2": {"txtId": 1841, "value": 220},
                    }
                }
            }
        },
    )
    sensor = TemperatureWidgetSensor(coordinator, "module-1", 1840)
    assert sensor.native_value == 20.5


def test_current_gear_sensor_exposes_name_and_attributes() -> None:
    """Current gear sensor maps int gear to integration option name."""
    coordinator = SimpleNamespace(
        data={"current_gear": 3, "current_slot_index": 2},
    )
    sensor = CurrentGearSensor(coordinator, "module-1")
    assert sensor.native_value == "gear_3"
    attrs = sensor.extra_state_attributes
    assert attrs["current_slot_index"] == 2
    assert "schedules" not in attrs


def test_heat_recovery_efficiency_is_computed_and_clamped() -> None:
    """Efficiency uses (supply-outdoor)/(extract-outdoor) formula."""
    coordinator = SimpleNamespace(
        data={
            "tiles": {
                1: {"params": {"txtId": 795, "value": 100}},   # 10.0
                2: {"params": {"txtId": 1841, "value": 250}},  # 25.0
                3: {"params": {"txtId": 1840, "value": 220}},  # 22.0
            }
        },
    )
    sensor = HeatRecoveryEfficiencySensor(coordinator, "module-1")
    assert sensor.native_value == 80.0


def test_heat_recovery_efficiency_returns_none_on_invalid_input() -> None:
    """Efficiency is unavailable when denominator is near zero."""
    coordinator = SimpleNamespace(
        data={
            "tiles": {
                1: {"params": {"txtId": 795, "value": 200}},
                2: {"params": {"txtId": 1841, "value": 200}},
                3: {"params": {"txtId": 1840, "value": 220}},
            }
        },
    )
    sensor = HeatRecoveryEfficiencySensor(coordinator, "module-1")
    assert sensor.native_value is None
