import numpy as np
import matplotlib.pyplot as plt

class Pendulum:
    def __init__(self, m, L, b, g=9.81):
        self.I = m * L**2
        self.b = b
        self.m = m
        self.L = L
        self.g = g
        self.theta = 0.1  # initial angle
        self.omega = 0.0  # initial angular velocity
    
    def step(self, tau, dt):
        alpha = (tau - self.b*self.omega - self.m*self.g*self.L*np.sin(self.theta)) / self.I
        self.omega += alpha * dt
        self.theta += self.omega * dt
        return self.theta, self.omega

class Actuator:
    def __init__(self, Km, Tm):
        self.Km = Km
        self.Tm = Tm
        self.tau = 0.0
    
    def step(self, u, dt):
        dtau = (self.Km * u - self.tau) / self.Tm
        self.tau += dtau * dt
        return self.tau

class PIDController:
    def __init__(self, Kp, Ki, Kd, dt, theta_ref=0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.theta_ref = theta_ref
        self.e_integral = 0.0
        self.e_last = 0.0
    
    def step(self, theta):
        e = self.theta_ref - theta
        self.e_integral += e * self.dt
        de = (e - self.e_last) / self.dt
        self.e_last = e
        u = self.Kp * e + self.Ki * self.e_integral + self.Kd * de
        return u

# Main simulation loop
dt = 0.001
time = np.arange(0, 2, dt)

pendulum = Pendulum(m=1, L=1, b=0.1)
actuator = Actuator(Km=10, Tm=0.05)
controller = PIDController(Kp=50, Ki=1, Kd=5, dt=dt)

theta_history = []

for t in time:
    theta, omega = pendulum.theta, pendulum.omega
    sensor_measurements = (theta, omega)
    u = controller.step(sensor_measurements[0])
    tau = actuator.step(u, dt)
    pendulum.step(tau, dt)
    theta_history.append(theta)

plt.plot(time, theta_history)
plt.xlabel('Time [s]')
plt.ylabel('Angle [rad]')
plt.title('Pendulum Angle vs Time')
plt.grid()
plt.show()
