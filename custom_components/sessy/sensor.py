"""Sensor to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    POWER_KILO_WATT,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    ELECTRIC_POTENTIAL_MILLIVOLT,
    ELECTRIC_CURRENT_MILLIAMPERE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    FREQUENCY_HERTZ
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand, SessySystemState, SessyP1State
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE, SCAN_INTERVAL_POWER
from .util import add_cache_command, enum_to_options_list, status_string_p1, status_string_system_state, unit_interval_to_percentage, devide_by_thousand
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    sensors = []

    await add_cache_command(hass, config_entry, SessyApiCommand.NETWORK_STATUS)
    sensors.append(
        SessySensor(hass, config_entry, "WiFi RSSI",
                    SessyApiCommand.NETWORK_STATUS, "wifi_sta.rssi",
                    SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                    entity_category=EntityCategory.DIAGNOSTIC)
    )

    if isinstance(device, SessyBattery):
        await add_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS, SCAN_INTERVAL_POWER)
        sensors.append(
            SessySensor(hass, config_entry, "System State",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state",
                        SensorDeviceClass.ENUM,
                        translation_key = "battery_system_state", transform_function=status_string_system_state,
                        options = enum_to_options_list(SessySystemState, status_string_system_state))
        )
        sensors.append(
            SessySensor(hass, config_entry, "System State Details",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state_details",
                        entity_category=EntityCategory.DIAGNOSTIC)
        )
        sensors.append(
            SessySensor(hass, config_entry, "State of Charge",
                        SessyApiCommand.POWER_STATUS, "sessy.state_of_charge",
                        SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                        transform_function=unit_interval_to_percentage, precision = 1)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Frequency",
                        SessyApiCommand.POWER_STATUS, "sessy.frequency",
                        SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, FREQUENCY_HERTZ,
                        transform_function=devide_by_thousand, precision = 3)
        )
        for phase_id in range(1,4): 
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Voltage",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.voltage_rms",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, ELECTRIC_POTENTIAL_MILLIVOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Current",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.current_rms",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, ELECTRIC_CURRENT_MILLIAMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Power",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_WATT)
            )


    elif isinstance(device, SessyP1Meter):
        await add_cache_command(hass, config_entry, SessyApiCommand.P1_STATUS, SCAN_INTERVAL_POWER)
        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        SessyApiCommand.P1_STATUS, "net_power_delivered",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_KILO_WATT, precision = 3)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Status",
                        SessyApiCommand.P1_STATUS, "state",
                        SensorDeviceClass.ENUM,
                        translation_key = "p1_state", transform_function=status_string_p1,
                        options = enum_to_options_list(SessyP1State, status_string_p1)
                        )
        )

    async_add_entities(sensors)
    
class SessySensor(SessyEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: function = None, translation_key: str = None,
                 options = None, entity_category: EntityCategory = None, precision: int = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function, translation_key=translation_key)

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_category = entity_category

        self._attr_suggested_display_precision = precision
        
        self._attr_options = options
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value