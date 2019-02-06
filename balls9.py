#!/usr/bin/python
#
"""This is a system that uses simulated elastic collisions among
groups of balls running in a circular track to produce notes and
chords.  The resulting sounds are somewhat musical."""
#
#
# Copyright 2017 David Talkin.
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
import Tkinter as tk
import math
import random
import array
import pyaudio
import time
import tune


def Elastic(m1, m2, v1, v2):
    """Returns a tuple of the velocities resulting from a perfectly
    elastic collision between masses m1 traveling at v1 and m2
    traveling at v2.  This simultaneously conserves momentum and energy."""
    vp2 =  ((m2 * v2) + (m1 * ((2.0 * v1) - v2))) / (m1 + m2)
    vp1 = vp2 + v2 - v1
    return vp1, vp2


class Ball(object):
    """Implements balls running in a frictionless circular track and
    adjusts their sizes and colors as a function of their momentum,
    direction, energy and mass."""
    e_low = 0.0
    e_high = 0.00000001
    e_gain_high = 0.0000001
    e_gain_low = 0.0
    mom_low = -0.001
    mom_high = 0.001
    angle_low = -1.0
    angle_high = 1.0

    def __init__(self, master, size, color, angle, velocity):
        self.master = master
        self.radius = int(size / 2)
        self.color = color
        self.angle = angle
        self.v = velocity
        self.m = size
        self.old_e = 0.0
        self.image = None
        self.mom_n = 127
        self.e_n = 127
        self.e_gain_n = 127
        self.ball_ind = None
        self.UpdateColor()

    def ResetRanges(self):
        Ball.e_low = 0.0
        Ball.e_high = 0.00000001
        Ball.e_gain_high = 0.0000001
        Ball.e_gain_low = 0.0
        Ball.mom_low = -0.000001
        Ball.mom_high = 0.000001

    def UpdateColor(self):
        """Generate RGB color weights based on the energy and moomentum of
        this ball."""
        mom = self.v * self.m
        if mom > Ball.mom_high:
            Ball.mom_high = mom
        if mom < Ball.mom_low:
            Ball.mom_low = mom
        e = 0.5 * self.v * self.v * self.m
        if e > Ball.e_high:
            Ball.e_high = e
        e_gain = abs(e - self.old_e)
        if e_gain > Ball.e_gain_high:
            Ball.e_gain_high = e_gain
        if e_gain < Ball.e_gain_low:
            Ball.e_gain_low = e_gain
        e_gain_range = Ball.e_gain_high - Ball.e_gain_low
        mom_range = Ball.mom_high - Ball.mom_low
        e_range = Ball.e_high - Ball.e_low
        self.mom_n = max(0, min(255, int((mom - Ball.mom_low) * 256.0 /
                                         mom_range)))
        self.e_n  = max(0, min(255, int((e - Ball.e_low) * 256.0 / e_range)))
        self.e_gain_n = max(0, min(255, int((e_gain - Ball.e_gain_low) * 256.0
                                            / e_gain_range)))

    def MakeColor(self):
        """Format a color specification from the RGB weights that is
        compatible with TK Draw methods."""
        color = ('#%2x%2x%2x' %
                 (self.mom_n, self.e_n, self.e_gain_n)).replace(' ', '0')
        return color

    def UpdatePosition(self, canvas, oradius, ocenter_x, ocenter_y):
        self.angle = math.fmod(self.angle + self.v, 2.0 * math.pi)
        x = (oradius * math.cos(self.angle)) + ocenter_x
        y = (oradius * math.sin(self.angle)) + ocenter_y
        self.Draw(canvas, x, y)

    def Draw(self, canvas, x, y):
        canvas.delete(self.image)
        x0 = x - self.radius
        y0 = y - self.radius
        x1 = x + self.radius
        y1 = y + self.radius
        col = self.MakeColor()
        self.image = canvas.create_oval(x0, y0, x1, y1, fill=col, outline=col)

    def WillCollide(self, other):
        """Determine if this ball will collide with other ball in the next
        time step."""
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
        t2 = sa + self.v - (oa + other.v)
        return (t1 * t2) <= 0.0

    def Collide(self, other):
        """If this ball will collide with other ball in the next time step,
        implement an elastic collision and update the balls' velocities."""
        if self.WillCollide(other):
            self.old_e = self.m * self.v * self.v * 0.5
            self.v, other.v = Elastic(self.m, other.m, self.v, other.v)
            self.UpdateColor()
            other.UpdateColor()
            return self.ball_ind, other.ball_ind
        return None


class Orbits(object):
    """Manages a collection of Balls running in a circular track."""

    def __init__(self, root, size, interval, balls=[], music=None):
        self.master = root
        self.music = music
        self.frame = tk.Frame(root)
        self.frame.pack(expand=tk.YES, fill=tk.BOTH)
        self.canvas = tk.Canvas(self.frame, width=size, height=size,
                                background='#303030')
        self.canvas.pack()
        self.balls = balls
        self.interval = interval
        self.radius = size * 0.3
        self.center_x = size * 0.5
        self.center_y = size * 0.5
        self.is_running = False
        self.after_id = None

    def UpdatePositions(self):
        """Run the ball collection for one time step, detect any collisions,
        and adjust the background color of the display as an ad hoc function
        of the system state.  Returns a set of all balls that collided."""
        for ball in self.balls:
            ball.UpdatePosition(self.canvas, self.radius, self.center_x,
                                self.center_y)
        count = 0
        collided = set([])
        while count < 5:
            collisions = 0
            for b in range(len(self.balls) - 1):
                for b2 in range(b + 1, len(self.balls)):
                    did_collide = self.balls[b].Collide(self.balls[b2])
                    if did_collide:
                        collisions += 1
                        collided.update(did_collide)
            count += 1
            if count > 4:
                print 'Collision Failure'
            if not collisions:
                break
        if collided:
            n = len(self.balls)
            r = b = g = 0
            for ball in self.balls:
                g += ball.e_n
                r += ball.mom_n
                b += ball.e_gain_n
            r /= n
            g /= n
            b /= n
            bg =  ('#%2x%2x%2x' % (r, g, b)).replace(' ', '0')
            self.canvas.configure(background=bg)
        return collided
                
    def Increment(self):
        hit_balls = self.UpdatePositions()
        for ball_ind in hit_balls:
            self.music.Ping(ball_ind)
        self.after_id = self.master.after(int(self.interval * 1000),
                                          self.Increment)

    def Start(self):
        if self.is_running:
            return
        self.is_running = True
        self.after_id = self.master.after(int(self.interval * 1000),
                                          self.Increment)

    def ClobberBalls(self):
        if self.after_id:
            self.master.after_cancel(self.after_id)
        self.after_id = None
        self.is_running = False
        for ball in self.balls:
            self.canvas.delete(ball.image)
        self.balls = []

    def AddBalls(self, new_balls):
        self.balls.extend(new_balls)
        self.balls[0].ResetRanges()


class Baller(object):
    """Make musical sounds using the motion of orbiting balls as an ad hoc
    driver.  Modulate the notes being played according to a
    user-specified chord sequence.  The initial velocities and masses
    of the balls are chosen randomly."""

    def __init__(self, root, orbit, interval, tonic='C3'):
        self.master = root
        self.n_range = [3, 7]
        self.size_range = [20,100]
        self.starts = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
        self.v_range = [-0.03, 0.03]
        self.orbit = orbit
        self.interval = int(interval * 1000)
        self.after_id = None
        self.audio = pyaudio.PyAudio()
        self.tonic = tonic
        self.fs = 22050.0
        self.music = tune.Music(self.audio, self.fs, self.tonic)
        self.switch_int = 3000
        self.tone_dur = 1.0
        self.tone_decay = 0.2
        self.prog_step_i = 0
        self.progression = ['I', 'vi', 'ii', 'IV', 'V']


    def SetProgression(self, prog_text):
        if not prog_text:
            self.progression = ['I', 'vi', 'ii', 'IV', 'V']
        else:
            self.progression = prog_text

    def CreateBalls(self):
        col = 'red'
        n_balls = int(0.5 + ((self.n_range[1] -
                              self.n_range[0]) * random.random()) +
                      self.n_range[0])
        balls = []
        self.music.StopAudioOutput()
        for i in range(n_balls):
            size = int(0.5 + ((self.size_range[1] -
                               self.size_range[0]) * random.random()) +
                       self.size_range[0])
            v = (((self.v_range[1] - self.v_range[0]) * random.random()) +
                 self.v_range[0])
            ball = Ball(self.master, size, col, self.starts[i], v)
            balls.append([size, ball])
        balls.sort(reverse=True)
        balls = [ball[1] for ball in balls]
        balls[0].ResetRanges()
        for i in range(len(balls)):
            balls[i].ball_ind = i
        # Get the semitone index of the base note re 'C'
        base_ind = int(0.5 + ((self.size_range[1] - balls[0].m) * 12.0 /
                              (self.size_range[1] - self.size_range[0])))
        # Now, find the note name that will become the tonic.
        n = tune.Notes(self.tonic, 1)
        self.tonic = n.GetNoteName(base_ind)
        if self.music and self.music.print_progression:
            print 'Tonic:', self.tonic
        self.music.SetupProgression(self.progression, self.tonic, 24)
        return balls

    def ProgressChordEvent(self, unused_event):
        if self.after_id:
            self.master.after_cancel(self.after_id)
        self.after_id = None
        self.ProgressChord()

    def ProgressChord(self):
        self.prog_step_i = (self.prog_step_i + 1) % len(self.progression)
        self.music.ChangeChord(self.prog_step_i)
        self.music.MakeChordCompatiblePingNotes(self.prog_step_i,
                                                len(self.orbit.balls))
        self.after_id = self.master.after(self.switch_int, self.ProgressChord)

    def ChangeNotes(self):
        self.music.ChangeChord(self.prog_step_i)
        self.music.MakeChordCompatiblePingNotes(self.prog_step_i,
                                                len(self.orbit.balls))

    def ToggleDetune(self, unused_event):
        if self.music:
            self.music.ToggleDetune()

    def TogglePing(self, unused_event):
        if self.music:
            self.music.TogglePing()

    def ToggleChord(self, unused_event):
        if self.music:
            self.music.ToggleChord()

    def TogglePrinting(self, unused_event):
        if self.music:
            self.music.TogglePrintProgression()

    def Restart(self, unused_event):
        self.master.after_cancel(self.after_id)
        self.after_id = None
        self.music.StopAudioOutput()
        self.Start()

    def Start(self):
        if not self.orbit:
            self.orbit = Orbits(self.master, 700, 0.01, music=self.music)
        self.orbit.ClobberBalls()
        self.orbit.AddBalls(self.CreateBalls())
        self.music.SetupAudioStream()
        self.ChangeNotes()
        self.music.StartAudio()
        self.orbit.canvas.focus_set()
        self.orbit.canvas.bind('<Button-1>', self.Restart)
        self.orbit.canvas.bind('<Button-2>', self.ProgressChordEvent)
        self.orbit.canvas.bind('<KeyPress-d>', self.ToggleDetune)
        self.orbit.canvas.bind('<KeyPress-p>', self.TogglePing)
        self.orbit.canvas.bind('<KeyPress-b>', self.ToggleChord)
        self.orbit.canvas.bind('<KeyPress-T>', self.TogglePrinting)
        self.after_id = self.master.after(self.switch_int, self.ProgressChord)
        self.orbit.Start()


def main(args):
    root = tk.Tk()
    root.title(args[0])
    b = Baller(root, None, 100.0, tonic='C3')
    if len(args) > 1:
        b.SetProgression(args[1:])
    b.Start()
    root.mainloop()

if __name__ == '__main__':
    main(sys.argv)
