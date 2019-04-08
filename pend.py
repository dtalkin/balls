#!/usr/bin/python
#
"""Simulates and displays a collection of potentially-interacting pendulums."""
#
#
# Copyright 2017-2019 David Talkin.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'dtalkin@gmail.com (David Talkin)'

import sys
import math
import time
import Tkinter as tk
import threading


# Just remember: F = ma  ;-)

g = 9.807  # m / (s*s)
g = 1.0


def Elastic(m1, m2, v1, v2):
    """Returns a tuple of the velocities resulting from a perfectly
    elastic collision between masses m1 traveling at v1 and m2
    traveling at v2.  This simultaneously conserves momentum and energy."""
    vp2 =  ((m2 * v2) + (m1 * ((2.0 * v1) - v2))) / (m1 + m2)
    vp1 = vp2 + v2 - v1
    return vp1, vp2


def DegToRad(deg):
    return 2.0 * math.pi * deg / 360.0


def RadToDeg(rad):
    return 360.0 * rad / (2.0 * math.pi)


class Bob(object):
    """Creates and manages a graphical representation of a collection of
    pendulums."""

    def __init__(self, width=700, height=700):
        self.root = tk.Tk()
        self.master = tk.Frame(self.root)
        self.master.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        self.canvas = tk.Canvas(self.master, height=height, width=width,
                                background='black')
        self.canvas.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        self.canvas.bind('<Configure>', self.Resize)
        self.canvas.bind('<Destroy>', self.Quit)
        self.height = height
        self.width = width
        self.pends = {}
        self.len_scale = min(height, width) * 1.1
        self.mass_scale = self.len_scale / 3.0

    def Quit(self, unused_event):
        pass

    def Resize(self, unused_event):
        pass

    def DrawPend(self, pend_id, angle, mass, length, color='red'):
        if pend_id in self.pends:
            pen, specs = self.pends.pop(pend_id)
            self.canvas.delete(pen[0], pen[1])
        pen = []
        specs = [angle, mass, length, color]
        x1 = self.width / 2
        y1 = self.height / 2
        radius = mass * self.mass_scale
        x2 = x1 + (math.cos(angle) * length * self.len_scale)
        y2 = y1 + (math.sin(angle) * length * self.len_scale)
        xa = x2 - radius
        ya = y2 - radius
        xb = x2 + radius
        yb = y2 + radius
        pen.append(self.canvas.create_line(x1,y1,x2,y2, fill=color))
        pen.append(self.canvas.create_oval(xa,ya,xb,yb, fill=color,
                                           outline=color))
        self.pends[pend_id] = [pen, specs]
        
        
        
class Pend(object):
    """Models the motion of a pendulum and its possible collision with
    others."""

    def __init__(self, mass=0.1, length=0.1, angle=0.0, color='red',
                 delta_t=0.001):
        """Args:
            mass: mass in kg
            length: length in meters
            angle: angle in degrees; increasing clockwise
        """
        self.mass = mass
        self.length = length
        self.color = color
        self.angle = DegToRad(angle)
        self.speed = 0.0
        self.del_t = delta_t
        self.sub_steps = 5

    def Step(self):
        f = self.mass * math.cos(self.angle) * g
        a = f / self.mass
        self.speed += a * self.del_t
        del_ang = self.speed * self.del_t / self.length
        self.angle = math.fmod(self.angle + del_ang, 2.0 * math.pi)

    def WillCollide(self, other):
        pi2 = 2.0 * math.pi
        piby2 = math.pi * 0.5
        if self.angle < 0.0:
            sa = pi2 + self.angle
        else:
            sa = self.angle
        if other.angle < 0.0:
            oa = pi2 + other.angle
        else:
            oa = other.angle
        if (sa < piby2) and (oa > math.pi):
            sa += pi2
        elif (oa < piby2) and (sa > math.pi):
            oa += pi2
        t1 = sa - oa
        self_av = self.speed * self.del_t / self.length
        other_av = other.speed * other.del_t / other.length
        t2 = sa + self_av - (oa + other_av)
        return (t1 * t2) <= 0.0

    def Collide(self, other):
        if self.WillCollide(other):
            self.speed, other.speed = Elastic(self.mass, other.mass,
                                              self.speed, other.speed)
            return True
        return False
        

class Pendulums(object):
    """Manages a collection of pendulums.  This runs two threads: one
    thread setps through the physical model in small time steps.  The
    other updates the display at longer intervals.
    """

    def __init__(self, pends, length=0.2, delta_t=0.0003,
                 update_interval=0.005):
        self.pends = []
        for mass, angle, color in pends:
            self.pends.append(Pend(mass, length, angle, color, delta_t))
        self.del_t = delta_t
        self.update = update_interval
        self.bob = Bob()
        self.after_id = None
        self.thread = None

    def RunPendulums(self):
        while True:
            time1 = time.time()
            for pend in self.pends:
                pend.Step()
            count = 0
            while count < 5:
                collisions = 0
                for i in range(len(self.pends) - 1):
                    for i2 in range(i + 1, len(self.pends)):
                        did_collide = self.pends[i].Collide(self.pends[i2])
                        if did_collide:
                            collisions += 1
                count += 1
                if count > 4:
                    print 'Collision failure'
                if not collisions:
                    break
            time2 = time.time()
            tsleep = self.del_t - (time2 - time1)
            if tsleep > 0.0:
                time.sleep(tsleep)

    def Run(self):
        if not self.thread:
            self.thread = threading.Thread(group=None, target=self.RunPendulums)
            self.thread.daemon = True
            self.thread.start()
        if self.after_id:
            self.bob.root.after_cancel(self.after_id)
            self.after_id = None
        for pend in self.pends:
            self.bob.DrawPend(pend, pend.angle, pend.mass, pend.length,
                              pend.color)
        self.after_id = self.bob.root.after(int(self.update * 1000),
                                            self.Run)


def DecodePendulums(specs):
    ret = []
    for spec in specs:
        bits = spec.split(',')
        if len(bits) != 3:
            sys.stderr.write('Ill-formed specification: %s\n' % (spec))
            continue
        try:
            mass, angle, color = float(bits[0]), float(bits[1]), bits[2]
        except ValueError:
            sys.stderr.write('Bad value in specification: %s\n' % (spec))
            continue
        ret.append([mass, angle, color])
    return ret


def main(args):
    if len(args) > 1:
        pends = DecodePendulums(args[1:])
    else:
        pends = [[0.1, 0.0, '#00ff00'], [0.1, 270.01, 'blue'],
                 [0.1, 180.0, 'red'], ]
    if not pends:
        sys.stderr.write('Usage: %s mass1,angle1,color1 '
                         'mass2,angle2,color2 ...\n' % (args[0]))
        sys.exit(-1)
    p = Pendulums(pends, length=0.4)
    p.Run()
    tk.mainloop()


if __name__ == '__main__':
    main(sys.argv)

