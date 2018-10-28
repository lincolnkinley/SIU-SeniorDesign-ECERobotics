#!/usr/bin/env python
from math import sin,cos,pi
import traceback
import numpy
import rospy
import tf2_ros
from tf2_geometry_msgs import do_transform_point
from tf.transformations import quaternion_from_euler
from geometry_msgs.msg import Twist,Pose,PointStamped,Point,Quaternion, Vector3,TransformStamped
from nav_msgs.msg import Odometry
from ecer2.Motor import Motor

max_linear_speed=2#temp
max_angular_speed=2#temp


totalOdom = numpy.array([0.0,0.0,0.0])

coefficients = numpy.array([
    [max_linear_speed*-sin(pi/6),max_linear_speed*-sin(5*pi/6),max_linear_speed*-sin(3*pi/2)],
    [max_linear_speed*cos(pi/6),max_linear_speed*cos(5*pi/6),max_linear_speed*cos(3*pi/2)],
    [max_angular_speed,max_angular_speed,max_angular_speed]])

last_velocities = numpy.array([0,0,0])
o_tf_broadcast = tf2_ros.TransformBroadcaster()
odom_publisher = rospy.Publisher("odom",Odometry,queue_size=50)
tf_buffer =tf2_ros.Buffer()


def getNewPosition(point):
    global tf_buffer
    transform = tf_buffer.lookup_transform("world","base_link",rospy.Time.now())
    p = PointStamped()
    p.point.x=point[0]
    p.point.y=point[1]
    newOdom = do_transform_point(p,transform)
    return newOdom




def publish_odom(current_velocities=None):
    global current_time
    global last_time
    global totalOdom
    global last_velocities
    global odom_publisher
    current_time = rospy.Time.now()
    print current_time
    print last_time
    dt = (current_time-last_time).to_sec()
    dist = last_velocities*float(dt)
    totalOdom[2]+=dist[2]#angular movement doesn't need to be changed tf frame
    print totalOdom
    quat = Quaternion(*quaternion_from_euler(0,0,totalOdom[2]))
    newPos=getNewPosition((dist[0],dist[1],0.))
    totalOdom[0]=newPos.point.x
    totalOdom[1]=newPos.point.y
    t = tf2_ros.TransformStamped()
    t.header.stamp=rospy.Time.now()
    t.header.frame_id='world'
    t.child_frame_id='base_link'
    t.transform.translation.x = totalOdom[0]
    t.transform.translation.y = totalOdom[1]
    t.transform.rotation = quat

    o_tf_broadcast.sendTransform(t)
    odom=Odometry()
    odom.header.stamp=current_time
    odom.header.frame_id="world"
    odom.pose.pose = Pose(Point(totalOdom[0],totalOdom[1],0.),quat)
    odom.child_frame_id="base_link"
    odom.twist.twist =  Twist(Vector3(last_velocities[0],last_velocities[1],0.), Vector3(0.,0.,last_velocities[2]))
    odom_publisher.publish(odom)
    if current_velocities is not None:
        last_velocities=current_velocities
    last_time=current_time




def build_control_callback(right,left,back):
    def callback(command):
        targetVelocities = numpy.array([command.linear.x,command.linear.y,command.angular.z])
        motorSpeeds = numpy.linalg.solve(coefficients,targetVelocities)
        maxAbs = max(abs(motorSpeeds))
        if maxAbs>1:
            motorSpeeds = motorSpeeds/maxAbs
            targetVelocities/=maxAbs
        motorSpeeds *=100
        right.speed = motorSpeeds[0]
        left.speed = motorSpeeds[1]
        back.speed = motorSpeeds[2]
        publish_odom(targetVelocities)
    return callback



def listener():
    global current_time
    global last_time
    global tf_buffer
    try:
        rospy.init_node('base_controller')
        current_time = rospy.Time.now()
        last_time = rospy.Time.now()
        print current_time
        print last_time
        publish_rate = rospy.Rate(4)
        tf_buffer  = tf2_ros.Buffer()
        tf_listener = tf2_ros.TransformListener(tf_buffer)
        with Motor(20,21) as right, Motor(19,26) as left, Motor(6,13) as back:
            rospy.Subscriber("cmd_vel",Twist,build_control_callback(right,left,back))
            while not rospy.is_shutdown():
                publish_rate.sleep()
                publish_odom()
    except Exception as e:
        traceback.print_exc()

if __name__=="__main__":
    listener()
