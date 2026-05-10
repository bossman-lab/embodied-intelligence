

# **Robot Control Tutorial**

This directory provides theoretical explanations and code implementations for robot control algorithms, with a focus on common methods such as PID control.

## Table of Contents

### PID Control Algorithm

* [PID Control Algorithm and Code Implementation](PID_Control.md) - Principles and implementations of PID control in Python/C.
* Supporting image resources – demonstrating control effects.

### Other Control Algorithms

* Kinematic Control (to be added)
* Trajectory Planning (to be added)
* Force Control (to be added)

## Learning Path

1. Start with the [PID Control Algorithm](PID_Control.md) to understand the basic control principles.
2. Explore how different control parameters affect system responses.
3. Try adjusting the PID parameters to achieve optimal control performance.
4. Proceed to study advanced control algorithms (to be updated).

## Code Example

This directory provides Python and C implementations of the PID control algorithm, which can be directly used in your projects.

### Python Example

```python
class PID:
    def __init__(self, Kp, Ki, Kd, setpoint=0, sample_time=0.01):
        # Initialize the PID controller
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.sample_time = sample_time
        
        self.prev_error = 0
        self.integral = 0
    
    def update(self, measured_value):
        # Calculate the control output
        error = self.setpoint - measured_value
        self.integral += error * self.sample_time
        derivative = (error - self.prev_error) / self.sample_time
        
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.prev_error = error
        
        return output
```

## Application Scenarios

* Motor speed/position control
* Robot joint control
* Balance scooter stabilization control
* Drone attitude control
* Temperature control systems

