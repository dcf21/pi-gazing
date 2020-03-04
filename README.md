# Pi Gazing

Pi Gazing is a project to build meteor cameras using Raspberry Pi computers
connected to CCTV cameras which are directed upwards to record the night sky.

The Raspberry Pi computer analyses the video feed in real time to search for
moving objects, recording the tracks of shooting stars, as well as satellites
and aircraft. We also see rarer phenomena: lightning strikes, fireworks, and
Iridian flares, caused by glints of light from solar panels on spacecraft.

Whenever a moving object is detected, the Raspberry Pi stores a video of the
object's path across the sky. Using a software package called *astrometry.net*,
the camera is able to automatically detect patterns of stars and calculate the
direction in which the camera is pointing, allowing the object's celestial
coordinates to be determined.

Each time the camera identifies a moving object, it compares the observation
with the records of other nearby cameras in the Pi Gazing network, to see if
the same object was seen from multiple locations. If so, the software compares
the position of the object in the sky as observed from the two locations, in
order to triangulate its altitude and speed. For shooting stars and satellites,
it is then possible to estimate the object's orbital elements.

The cameras also take a series of long-exposure still photos each night. These
are used by the software to determine the direction the camera is pointing in,
as well as to calibrate any distortions which may be present in the lens used
(for example, barrel distortion).

These still images also allow you to watch how the constellations circle
overhead as the night progresses, or how they change with the seasons. You can
see the changing phases of the Moon, or watch the planets move across the sky.

To find out more about the Pi Gazing project, you should [visit our project
website](https://pigazing.dcford.org.uk/). There, you can browse the entire
archive of observations recorded by our cameras.

These GitHub pages contain the program code and hardware designs that we use.
They're all open source, and if you want to set up your own camera using our
software, you should be able to find all the information you need here.

## Acknowledgments

Pi Gazing is being developed by astronomer [Dominic
Ford](https://dcford.org.uk).

It is based on code that was written for [Cambridge Science
Centre](http://www.cambridgesciencecentre.org/)'s MeteorPi project, which was
created by Dominic Ford with generous support from the Raspberry Pi Foundation,
and MathWorks.

## Social media

You can follow us on [Twitter](https://twitter.com/meteorpi) and
[Facebook](https://www.facebook.com/meteorpicamera).
