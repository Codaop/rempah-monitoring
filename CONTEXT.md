# REMPAH

IoT-integrated cardamom distillation system with PID temperature control for essential oil yield improvement.

## Language

**Producer**:
An organisation or farm that owns devices; the tenant boundary of the system.
_Avoid_: farm, company, account

**Operator**:
A person with dashboard access, registered by the system admin, who monitors and commands the devices of their producer.
_Avoid_: user, account

**Device**:
A physical distillation unit (ESP32 plus its sensors and actuators) that produces telemetry and executes commands.
_Avoid_: machine, unit

**Monitoring Session**:
A supervised period of operation covering the devices an operator selected before the session opened. Contains zero, one, or many batches per device.
_Avoid_: session alone (ambiguous)

**Batch**:
A single distillation run on one device within a monitoring session, from ignition to completion or drain, bounded by device-state transitions.
_Avoid_: run, distillation run

**Device State**:
The coarse operating mode of a device (`IDLE / PREHEAT / DISTILLING / DRAINING / ERROR / ESTOP`) and the ground truth for command validation.
_Avoid_: status, mode

**Command**:
A dashboard instruction to a device carrying the state the operator expects the device to be in (`expected_current_state`), which the bridge validates before forwarding.
_Avoid_: action, instruction

**Emergency Stop**:
A command exempt from state validation that bypasses every check and goes straight to the device.

**Telemetry**:
Periodic sensor readings from a device (temperature, gas pressure, water level, drip count, flame). Used for monitoring only, never for validation.

**sensor_logs**:
Raw telemetry rows tied to a batch; kept while the batch is active plus a short grace period, then purged.
_Avoid_: raw data, logs

**BatchLog**:
The retained aggregate record of a batch (peak temperature, duration, yield, temperature profile).
_Avoid_: summary

**Charge Mass**:
The feedstock mass an operator enters when a batch starts, used to derive the target yield.
_Avoid_: feed, load

**Estimated Yield**:
The yield the bridge computes from telemetry and drip data against a batch's target, together with an estimated finish time.