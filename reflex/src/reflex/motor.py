from dynamixel_msgs.msg import JointState
from dynamixel_controllers.srv import TorqueEnable
from dynamixel_controllers.srv import SetSpeed
import rospy
from std_msgs.msg import Float64

import reflex_msgs.msg


class Motor(object):
    def __init__(self, name):
        '''
        Assumes that "name" is the name of the controller with a preceding
        slash, e.g. /reflex_takktile_f1
        '''
        self.name = name[1:]
        self.DEFAULT_MOTOR_SPEED = rospy.get_param(name + '/default_motor_speed')
        self.MAX_MOTOR_SPEED = rospy.get_param(name + '/max_motor_speed')
        self.MAX_MOTOR_TRAVEL = rospy.get_param(name + '/max_motor_travel')
        self.OVERLOAD_THRESHOLD = rospy.get_param(name + '/overload_threshold')
        self.motor_msg = reflex_msgs.msg.Motor()
        self.motor_cmd = 0.0
        self.speed = 0.0
        self.reset_motor_speed()

    def get_current_joint_angle(self):
        return self.motor_msg.joint_angle

    def get_load(self):
        return self.motor_msg.load

    def get_motor_msg(self):
        return self.motor_msg

    def get_commanded_position(self):
        return self.motor_cmd

    def get_commanded_speed(self):
        return self.speed

    def set_motor_angle(self, goal_pos):
        '''
        Bounds the given position command and sets it to the motor
        '''
        self.motor_cmd = self.check_motor_angle_command(goal_pos)

    def check_motor_angle_command(self, angle_command):
        '''
        Returns given command if within the allowable range,
        returns bounded command if out of range
        '''
        bounded_command = min(max(angle_command, 0.0), self.MAX_MOTOR_TRAVEL)
        return bounded_command

    def set_motor_speed(self, goal_speed):
        '''
        Bounds the given position command and sets it to the motor
        '''
        self.speed = self.check_motor_speed_command(goal_speed)

    def check_motor_speed_command(self, goal_speed):
        '''
        Returns absolute of given command if within the allowable range,
        returns bounded command if out of range. Always returns positive
        '''
        bounded_command = min(abs(goal_speed), self.MAX_MOTOR_SPEED)
        return bounded_command

    def reset_motor_speed(self):
        '''
        Resets speed to default
        '''
        self.speed = self.DEFAULT_MOTOR_SPEED

    def set_motor_velocity(self, goal_vel):
        '''
        Sets speed and commands finger in or out based on sign of velocity
        '''
        self.set_motor_speed(goal_vel)
        if goal_vel > 0.0:
            self.set_motor_angle(self.MAX_MOTOR_TRAVEL)
        elif goal_vel <= 0.0:
            self.set_motor_angle(0.0)

    def loosen_if_overloaded(self, load):
        if abs(load) > self.OVERLOAD_THRESHOLD:
            rospy.logwarn("Motor %s overloaded at %f, loosening" % (self.name, load))
            self.loosen()

    def tighten(self, tighten_angle=0.05):
        '''
        Takes the given angle offset in radians and tightens the motor
        '''
        self.set_motor_angle(self.motor_msg.joint_angle + tighten_angle)

    def loosen(self, loosen_angle=0.05):
        '''
        Takes the given angle offset in radians and loosens the motor
        '''
        self.set_motor_angle(self.motor_msg.joint_angle - loosen_angle)

    def receive_state_cb(self, data):
        self.motor_msg.joint_angle = data.joint_angle
        self.motor_msg.raw_angle = data.raw_angle
        self.motor_msg.velocity = data.velocity

        # Rolling filter of noisy data
        load_filter = 0.1
        self.motor_msg.load = load_filter * data.load + (1 - load_filter) * self.motor_msg.load
        self.loosen_if_overloaded(self.motor_msg.load)

        self.motor_msg.voltage = data.voltage
        self.motor_msg.temperature = data.temperature
        self.motor_msg.error_state = data.error_state
