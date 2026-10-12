import { Battery, Droplets, Thermometer, Zap } from "lucide-react";
import type { Device } from "../types/device";
import { sensorReadings } from "../services/sensorReadings";
export function SensorReadings({ device }: { device: Device }) {
  return (
    <div className="sensor-values">
      {sensorReadings(device).map((reading) => {
        const Icon = {
          temperature_sensor: Thermometer,
          humidity_sensor: Droplets,
          battery_sensor: Battery,
          power_monitoring: Zap,
        }[reading.cap];
        return (
          <div key={reading.cap}>
            <Icon size={17} />
            <strong>
              {reading.value}
              <small>{reading.unit}</small>
            </strong>
            <span>{reading.label}</span>
          </div>
        );
      })}
    </div>
  );
}
