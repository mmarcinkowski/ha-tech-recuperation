"""Sensors for Tech Recuperation integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, GEAR_VALUE_TO_NAME, TEMP_SENSOR_NAMES, TEMP_SENSOR_TXTIDS, TEMPERATURE_DIVISOR
from .entity import TechRecuperationEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])

    entities: list[SensorEntity] = [
        CurrentGearSensor(coordinator, udid),
        HeatRecoveryEfficiencySensor(coordinator, udid),
    ]

    # Add known temperature sensors if present in tile data
    seen_txt_ids: set[int] = set()
    for tile in coordinator.data.get("tiles", {}).values():
        params = tile.get("params", {})
        txt_id = params.get("txtId")
        if txt_id in TEMP_SENSOR_TXTIDS:
            seen_txt_ids.add(int(txt_id))
            entities.append(TemperatureTileSensor(coordinator, udid, int(txt_id)))

    # Also detect temp widgets inside type 6 tiles
    for tile in coordinator.data.get("tiles", {}).values():
        params = tile.get("params", {})
        for widget_key in ("widget1", "widget2"):
            widget = params.get(widget_key, {})
            txt_id = widget.get("txtId")
            if txt_id in TEMP_SENSOR_TXTIDS and int(txt_id) not in seen_txt_ids:
                seen_txt_ids.add(int(txt_id))
                entities.append(TemperatureWidgetSensor(coordinator, udid, int(txt_id)))

    async_add_entities(entities)


class TemperatureTileSensor(TechRecuperationEntity, SensorEntity):
    """Temperature sensor sourced from tile params.value."""

    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, udid: str, txt_id: int) -> None:
        super().__init__(coordinator, udid)
        self._txt_id = txt_id
        self._attr_unique_id = f"{udid}_temp_tile_{txt_id}"
        self._attr_name = TEMP_SENSOR_NAMES.get(txt_id, f"Temperature {txt_id}")

    @property
    def native_value(self) -> float | None:
        for tile in self.coordinator.data.get("tiles", {}).values():
            params = tile.get("params", {})
            if params.get("txtId") == self._txt_id:
                value = params.get("value")
                if value is None:
                    return None
                return round(float(value) / TEMPERATURE_DIVISOR, 1)
        return None


class TemperatureWidgetSensor(TechRecuperationEntity, SensorEntity):
    """Temperature sensor sourced from tile widget values."""

    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, udid: str, txt_id: int) -> None:
        super().__init__(coordinator, udid)
        self._txt_id = txt_id
        self._attr_unique_id = f"{udid}_temp_widget_{txt_id}"
        self._attr_name = TEMP_SENSOR_NAMES.get(txt_id, f"Temperature {txt_id}")

    @property
    def native_value(self) -> float | None:
        for tile in self.coordinator.data.get("tiles", {}).values():
            params = tile.get("params", {})
            for widget_key in ("widget1", "widget2"):
                widget = params.get(widget_key, {})
                if widget.get("txtId") == self._txt_id:
                    value = widget.get("value")
                    if value is None:
                        return None
                    return round(float(value) / TEMPERATURE_DIVISOR, 1)
        return None


class CurrentGearSensor(TechRecuperationEntity, SensorEntity):
    """Current gear derived from active schedule slot."""

    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_current_gear"
        self._attr_name = "Current Gear"

    @property
    def native_value(self) -> str:
        return GEAR_VALUE_TO_NAME.get(self.coordinator.data.get("current_gear", 1), "gear_1")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "current_slot_index": self.coordinator.data.get("current_slot_index", 0),
        }


class HeatRecoveryEfficiencySensor(TechRecuperationEntity, SensorEntity):
    """Calculated heat recovery efficiency."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_heat_recovery_efficiency"
        self._attr_name = "Heat Recovery Efficiency"

    def _temp_by_txt(self, txt_id: int) -> float | None:
        for tile in self.coordinator.data.get("tiles", {}).values():
            params = tile.get("params", {})
            if params.get("txtId") == txt_id and params.get("value") is not None:
                return float(params["value"]) / TEMPERATURE_DIVISOR
            for widget_key in ("widget1", "widget2"):
                widget = params.get(widget_key, {})
                if widget.get("txtId") == txt_id and widget.get("value") is not None:
                    return float(widget["value"]) / TEMPERATURE_DIVISOR
        return None

    @property
    def native_value(self) -> float | None:
        outdoor = self._temp_by_txt(795)
        extract = self._temp_by_txt(1841)
        supply = self._temp_by_txt(1840)

        if outdoor is None or extract is None or supply is None:
            return None
        denominator = extract - outdoor
        if abs(denominator) < 0.001:
            return None
        eff = (supply - outdoor) / denominator * 100
        return round(max(0.0, min(100.0, eff)), 1)
